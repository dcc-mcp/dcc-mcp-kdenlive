// SPDX-License-Identifier: GPL-3.0-or-later
#include "bridge_server.h"
#include <QCoreApplication>
#include <QJsonDocument>
#include <QJsonParseError>
#include <QTcpSocket>
#include <QThread>
#include <QTimer>
#include <memory>
#include <utility>

namespace {
constexpr int MaxFrame = 1024 * 1024;
QJsonObject error(const QString &code) { return {{QStringLiteral("error"), code}}; }
bool sameToken(const QByteArray &a, const QByteArray &b)
{
    if (a.size() != b.size()) return false;
    unsigned char different = 0;
    for (int i = 0; i < a.size(); ++i) different |= a[i] ^ b[i];
    return different == 0;
}
}

BridgeServer::BridgeServer(QByteArray token, Handler handler, QObject *parent)
    : QTcpServer(parent), m_token(std::move(token)), m_handler(std::move(handler))
{
    setMaxPendingConnections(8);
    connect(this, &QTcpServer::newConnection, this, [this]() {
        while (hasPendingConnections()) {
            auto *socket = nextPendingConnection();
            if (findChildren<QTcpSocket *>(QString(), Qt::FindDirectChildrenOnly).size() > 8) {
                socket->abort(); socket->deleteLater(); continue;
            }
            socket->setReadBufferSize(MaxFrame + 1);
            auto buffer = std::make_shared<QByteArray>();
            auto handled = std::make_shared<bool>(false);
            connect(socket, &QTcpSocket::disconnected, socket, &QObject::deleteLater);
            QTimer::singleShot(5000, socket, [socket]() { socket->abort(); });
            connect(socket, &QTcpSocket::readyRead, socket, [this, socket, buffer, handled]() {
                if (*handled) return;
                buffer->append(socket->readAll());
                if (buffer->size() > MaxFrame) { *handled = true; socket->abort(); return; }
                if (!buffer->contains('\n')) return;
                *handled = true; // Exactly one request per connection, no pipelining.
                QJsonParseError parse;
                const auto document = QJsonDocument::fromJson(buffer->trimmed(), &parse);
                const auto request = document.object();
                QJsonObject response;
                if (parse.error != QJsonParseError::NoError || !document.isObject()
                    || !request.value(QStringLiteral("id")).isString()
                    || !request.value(QStringLiteral("params")).isObject()
                    || request.value(QStringLiteral("protocol")).toInt(-1) != 1) {
                    response = error(QStringLiteral("invalid_request"));
                } else if (!sameToken(request.value(QStringLiteral("token")).toString().toUtf8(), m_token)) {
                    response = error(QStringLiteral("unauthorized"));
                } else if (request.value(QStringLiteral("host_pid")).toDouble() != QCoreApplication::applicationPid()) {
                    response = error(QStringLiteral("host_mismatch"));
                } else {
                    Q_ASSERT(QThread::currentThread() == QCoreApplication::instance()->thread());
                    response = m_handler(request.value(QStringLiteral("method")).toString(),
                                         request.value(QStringLiteral("params")).toObject());
                }
                response.insert(QStringLiteral("id"), request.value(QStringLiteral("id")));
                response.insert(QStringLiteral("protocol"), 1);
                response.insert(QStringLiteral("host_pid"), double(QCoreApplication::applicationPid()));
                const auto wire = QJsonDocument(response).toJson(QJsonDocument::Compact);
                if (wire.size() > MaxFrame - 1) { socket->abort(); return; }
                socket->write(wire + '\n');
                socket->disconnectFromHost();
            });
        }
    });
}

bool BridgeServer::start(quint16 port)
{
    if (m_token.size() < 32) return false;
    return listen(QHostAddress::LocalHost, port);
}
