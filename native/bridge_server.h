// SPDX-License-Identifier: GPL-3.0-or-later
#pragma once
#include <QJsonObject>
#include <QTcpServer>
#include <functional>

// Owned by the host GUI thread. The handler must call native model commands,
// never synthesize UI events or run arbitrary scripts.
class BridgeServer : public QTcpServer
{
public:
    using Handler = std::function<QJsonObject(const QString &, const QJsonObject &)>;
    BridgeServer(QByteArray token, Handler handler, QObject *parent = nullptr);
    bool start(quint16 port);
private:
    QByteArray m_token;
    Handler m_handler;
};
