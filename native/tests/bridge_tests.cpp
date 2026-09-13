// SPDX-License-Identifier: GPL-3.0-or-later
#include "bridge_server.h"
#include <QCoreApplication>
#include <QJsonDocument>
#include <QTcpSocket>
#include <QtTest>

class BridgeTests : public QObject
{
    Q_OBJECT
private Q_SLOTS:
    void weakTokenDoesNotListen()
    {
        BridgeServer server("short", [](const QString &, const QJsonObject &) { return QJsonObject(); });
        QVERIFY(!server.start(0));
    }
    void request_data()
    {
        QTest::addColumn<QString>("token");
        QTest::addColumn<int>("pidOffset");
        QTest::addColumn<int>("protocol");
        QTest::addColumn<QString>("expectedError");
        QTest::newRow("valid") << QString(32, QLatin1Char('a')) << 0 << 1 << QString();
        QTest::newRow("wrong-token") << QString(32, QLatin1Char('b')) << 0 << 1 << QStringLiteral("unauthorized");
        QTest::newRow("wrong-host") << QString(32, QLatin1Char('a')) << 1 << 1 << QStringLiteral("host_mismatch");
        QTest::newRow("wrong-protocol") << QString(32, QLatin1Char('a')) << 0 << 2 << QStringLiteral("invalid_request");
    }
    void request()
    {
        QFETCH(QString, token); QFETCH(int, pidOffset); QFETCH(int, protocol); QFETCH(QString, expectedError);
        int calls = 0;
        BridgeServer server(QByteArray(32, 'a'), [&calls](const QString &method, const QJsonObject &) {
            ++calls;
            return QJsonObject{{QStringLiteral("result"), QJsonObject{{QStringLiteral("method"), method}}}};
        });
        QVERIFY(server.start(0));
        QCOMPARE(server.serverAddress(), QHostAddress(QHostAddress::LocalHost));
        QTcpSocket socket;
        socket.connectToHost(QHostAddress::LocalHost, server.serverPort());
        QVERIFY(socket.waitForConnected());
        const auto wire = QJsonDocument(QJsonObject{
            {QStringLiteral("id"), QStringLiteral("test")}, {QStringLiteral("token"), token},
            {QStringLiteral("protocol"), protocol}, {QStringLiteral("host_pid"), double(QCoreApplication::applicationPid() + pidOffset)},
            {QStringLiteral("method"), QStringLiteral("project_state")}, {QStringLiteral("params"), QJsonObject{}}}).toJson(QJsonDocument::Compact) + '\n';
        // Fragmented TCP delivery must still execute exactly once.
        socket.write(wire.left(5)); socket.flush();
        QTest::qWait(10); QCOMPARE(calls, 0);
        socket.write(wire.mid(5)); socket.flush();
        QTRY_VERIFY(socket.canReadLine());
        const auto reply = QJsonDocument::fromJson(socket.readLine()).object();
        QCOMPARE(reply.value(QStringLiteral("id")).toString(), QStringLiteral("test"));
        QCOMPARE(reply.value(QStringLiteral("error")).toString(), expectedError);
        QCOMPARE(calls, expectedError.isEmpty() ? 1 : 0);
    }
    void oversizedDoesNotDispatch()
    {
        int calls = 0;
        BridgeServer server(QByteArray(32, 'a'), [&calls](const QString &, const QJsonObject &) { ++calls; return QJsonObject{}; });
        QVERIFY(server.start(0));
        QTcpSocket socket;
        socket.connectToHost(QHostAddress::LocalHost, server.serverPort());
        QVERIFY(socket.waitForConnected());
        socket.write(QByteArray(1024 * 1024 + 1, 'x'));
        QTRY_COMPARE(socket.state(), QAbstractSocket::UnconnectedState);
        QCOMPARE(calls, 0);
    }
};
QTEST_GUILESS_MAIN(BridgeTests)
#include "bridge_tests.moc"
