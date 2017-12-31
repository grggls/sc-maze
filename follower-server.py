from twisted.internet import reactor
from twisted.internet.endpoints import TCP4ClientEndpoint, connectProtocol
from twisted.internet.protocol import Protocol, Factory, ClientFactory


class EventProtocol(Protocol):
    # events might come in chunks, handle responsibly
    def dataReceived(self, data):
        self.splitEvent(data)

    # split along delimiter (\n), chomp trailing newline as unused, grab event id 
    # before storing away so we can put these in order. ensure we have utf8
    def splitEvent(self, payload):
        for event in payload.split(delimiter)[:-1]:
            events[int(event[0])] = event.decode('utf-8')


class UserProtocol(Protocol):
    # only data received from user should be userId
    def dataReceived(self, data):
        userId = data.strip(delimiter)
        users[userId] = self.transport

    def sendUserMessage(self, user, data):
        users[user].sendMessage(data)

if __name__ == '__main__':
    events = {}
    users = {}
    followers = {}

    delimiter = '\n'
    separator = '|'

    event_source_factory = Factory()
    event_source_factory.protocol = EventProtocol

    user_clients_factory = Factory()
    user_clients_factory.protocol = UserProtocol

    reactor.listenTCP(9090, event_source_factory)
    reactor.listenTCP(9099, user_clients_factory)
    reactor.run()
