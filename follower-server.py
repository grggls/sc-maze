from twisted.internet.protocol import Protocol, Factory
from twisted.internet import reactor

class EventSource(Protocol):
    def dataReceived(self, data):
        print 'EventSource data:' + data
        #self.transport.write('EventSource data:' + data)
        #self.transport.loseConnection()

class UserClients(Protocol):
    def dataReceived(self, data):
        print 'UserClients data:' + data
        #self.transport.write('UserClients data:' + data)
        #self.transport.loseConnection()

if __name__ == '__main__':
    event_source_factory = Factory()
    event_source_factory.protocol = EventSource

    user_clients_factory = Factory()
    user_clients_factory.protocol = UserClients

    reactor.listenTCP(9090, event_source_factory)
    print 'Event Source listener started'
    reactor.listenTCP(9099, user_clients_factory)
    print 'User Clients  listener started'
    reactor.run()
