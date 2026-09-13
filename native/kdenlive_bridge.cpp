// SPDX-License-Identifier: GPL-3.0-or-later
#include "bridge_server.h"
#include "core.h"
#include "mainwindow.h"
#include "bin/projectitemmodel.h"
#include "doc/docundostack.hpp"
#include "doc/kdenlivedoc.h"
#include "project/projectmanager.h"
#include "timeline2/view/timelinewidget.h"
#include <QApplication>
#include <QCryptographicHash>
#include <QJsonArray>
#include <QJsonDocument>
#include <QThread>
#include <QSet>
#include <QUuid>
#include <cmath>
#include <limits>

namespace {
const QString session = QUuid::createUuid().toString(QUuid::WithoutBraces);
QJsonObject failure(const char *code) { return {{QStringLiteral("error"), QString::fromLatin1(code)}}; }
bool integer(const QJsonObject &p, const char *key)
{
    const auto v = p.value(QString::fromLatin1(key));
    return v.isDouble() && v.toDouble() >= 0 && v.toDouble() <= std::numeric_limits<int>::max()
        && std::floor(v.toDouble()) == v.toDouble();
}
QString revision(const std::shared_ptr<TimelineItemModel> &model, KdenliveDoc *doc)
{
    // Includes model serialization, undo cursor, document and active sequence.
    // GUI edits between read and command invalidate the caller's revision.
    const auto state = session + model->uuid().toString() + doc->url().toString()
        + QString::number(pCore->undoStack()->index()) + model->sceneList(QString(), QString());
    return QString::fromLatin1(QCryptographicHash::hash(state.toUtf8(), QCryptographicHash::Sha256).toHex());
}
QJsonObject snapshot(const std::shared_ptr<TimelineItemModel> &model, KdenliveDoc *doc)
{
    QJsonArray tracks;
    for (int r = 0; r < model->rowCount(); ++r) {
        const auto track = model->index(r, 0);
        QJsonArray clips;
        for (int c = 0; c < model->rowCount(track); ++c) {
            const auto item = model->index(c, 0, track);
            const int id = model->data(item, TimelineModel::ItemIdRole).toInt();
            if (!model->isClip(id)) continue;
            clips.append(QJsonObject{{QStringLiteral("clip_id"), id},
                                     {QStringLiteral("bin_id"), model->getClipBinId(id)},
                                     {QStringLiteral("position"), model->getClipPosition(id)},
                                     {QStringLiteral("duration"), model->getClipPlaytime(id)}});
        }
        tracks.append(QJsonObject{{QStringLiteral("track_id"), model->data(track, TimelineModel::ItemIdRole).toInt()},
                                  {QStringLiteral("name"), model->data(track, TimelineModel::NameRole).toString()},
                                  {QStringLiteral("audio"), model->data(track, TimelineModel::IsAudioRole).toBool()},
                                  {QStringLiteral("clips"), clips}});
    }
    return {{QStringLiteral("revision"), revision(model, doc)},
            {QStringLiteral("sequence_id"), model->uuid().toString()},
            {QStringLiteral("project_path"), doc->url().toLocalFile()},
            {QStringLiteral("modified"), doc->isModified()},
            {QStringLiteral("duration_frames"), model->duration()},
            {QStringLiteral("tracks"), tracks},
            {QStringLiteral("can_undo"), pCore->undoStack()->canUndo()},
            {QStringLiteral("can_redo"), pCore->undoStack()->canRedo()}};
}
QJsonObject dispatch(const QString &method, const QJsonObject &params)
{
    Q_ASSERT(QThread::currentThread() == qApp->thread());
    if (QApplication::activeModalWidget()) return failure("host_modal");
    if (method == QStringLiteral("handshake")) {
        if (!params.isEmpty()) return failure("invalid_params");
        return {{QStringLiteral("result"), QJsonObject{
            {QStringLiteral("session_id"), session},
            {QStringLiteral("window_handle"), QString::number(quintptr(pCore->window()->winId()))},
            {QStringLiteral("host_version"), QStringLiteral("26.08.1")},
            {QStringLiteral("bridge_version"), QStringLiteral("0.1.0")},
            {QStringLiteral("capabilities"), QJsonArray{
                QStringLiteral("project_state"), QStringLiteral("insert_clip"),
                QStringLiteral("move_clip"), QStringLiteral("undo"), QStringLiteral("redo")}}}}};
    }
    const QSet<QString> methods{QStringLiteral("project_state"), QStringLiteral("insert_clip"),
                               QStringLiteral("move_clip"), QStringLiteral("undo"), QStringLiteral("redo")};
    if (!methods.contains(method)) return failure("unsupported_method");
    auto *widget = pCore->window()->getCurrentTimeline();
    auto *doc = pCore->projectManager()->current();
    if (!widget || widget->loading || !doc || !widget->model() || widget->model()->isClosed) return failure("host_not_ready");
    const auto model = widget->model();
    if (method == QStringLiteral("project_state")) {
        if (!params.isEmpty()) return failure("invalid_params");
        return {{QStringLiteral("result"), snapshot(model, doc)}};
    }
    QSet<QString> allowed{QStringLiteral("expected_revision")};
    if (method == QStringLiteral("insert_clip") || method == QStringLiteral("move_clip")) {
        allowed.insert(QStringLiteral("track_id")); allowed.insert(QStringLiteral("position"));
        allowed.insert(method == QStringLiteral("insert_clip") ? QStringLiteral("bin_id") : QStringLiteral("clip_id"));
        if (!integer(params, "track_id") || !integer(params, "position")) return failure("invalid_params");
        if (!model->isTrack(params.value(QStringLiteral("track_id")).toInt())) return failure("unknown_track");
    }
    for (auto i = params.begin(); i != params.end(); ++i) if (!allowed.contains(i.key())) return failure("invalid_params");
    if (params.value(QStringLiteral("expected_revision")).toString().isEmpty()
        || params.value(QStringLiteral("expected_revision")).toString() != revision(model, doc)) return failure("stale_revision");
    int insertedId = -1;
    if (method == QStringLiteral("insert_clip")) {
        const auto binId = params.value(QStringLiteral("bin_id")).toString();
        if (binId.isEmpty() || !pCore->projectItemModel()->hasClip(binId)) return failure("unknown_bin_clip");
        if (!model->requestClipInsertion(binId, params.value(QStringLiteral("track_id")).toInt(),
                                        params.value(QStringLiteral("position")).toInt(), insertedId, true, true, false)) return failure("edit_rejected");
    } else if (method == QStringLiteral("move_clip")) {
        if (!integer(params, "clip_id") || !model->isClip(params.value(QStringLiteral("clip_id")).toInt())) return failure("unknown_clip");
        if (!model->requestClipMove(params.value(QStringLiteral("clip_id")).toInt(),
                                   params.value(QStringLiteral("track_id")).toInt(),
                                   params.value(QStringLiteral("position")).toInt(), true, true, true)) return failure("edit_rejected");
    } else if (method == QStringLiteral("undo")) {
        if (!pCore->undoStack()->canUndo()) return failure("nothing_to_undo");
        pCore->undoStack()->undo();
    } else if (method == QStringLiteral("redo")) {
        if (!pCore->undoStack()->canRedo()) return failure("nothing_to_redo");
        pCore->undoStack()->redo();
    }
    // Undo can change the active sequence. Never return the previously held model.
    auto *current = pCore->window()->getCurrentTimeline();
    auto *currentDoc = pCore->projectManager()->current();
    if (!current || !currentDoc || !current->model() || current->loading || current->model()->isClosed)
        return failure("edit_applied_state_unavailable");
    auto result = snapshot(current->model(), currentDoc);
    if (insertedId >= 0) result.insert(QStringLiteral("inserted_clip_id"), insertedId);
    return {{QStringLiteral("result"), result}};
}
}

void startDccBridge()
{
    // Opt-in at launch; no listener and no native popup in a normal launch.
    const auto token = qgetenv("DCC_KDENLIVE_BRIDGE_TOKEN");
    bool valid = false;
    const auto port = qEnvironmentVariableIntValue("DCC_KDENLIVE_BRIDGE_PORT", &valid);
    if (!valid || port <= 0 || port > 65535 || token.size() < 32) return;
    auto *server = new BridgeServer(token, dispatch, pCore->window());
    if (!server->start(quint16(port))) { qWarning("DCC bridge could not listen"); delete server; }
}
