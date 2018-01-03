from twisted.internet import reactor, threads, protocol
from twisted.internet.task import LoopingCall
from twisted.internet.endpoints import TCP4ClientEndpoint, connectProtocol
from twisted.internet.protocol import Protocol, Factory, ClientFactory

class EventFactory(protocol.ClientFactory):
    def __init__(self):
        self.nextEvent = 1

    def buildProtocol(self, addr):
        p = EventProtocol()
        p.factory = self
        return p

class EventProtocol(Protocol):
    def dataReceived(self, data):
        # split along delimiter (\n), chomp trailing newline as unused, grab event id
        # before storing away so we can put these in order. ensure we have utf8
        message = data.rstrip()
        for event in message.split(delimiter):
            sequence = event.split(separator)[0]
            try:
                events[int(sequence)] = event
            except:
                pass    # bad event?


class UserProtocol(Protocol):
    def connectionMade(self):
        try:
            self.transport.setTcpKeepAlive(1)
        except AttributeError: pass

    # only data received from user should be userId
    def dataReceived(self, data):
        userId = data.strip(delimiter)
        users[int(userId)] = self
        followers[int(userId)] = []

def messageDispatcher(message):
    fields = message.split(separator)
    sequence = fields[0]
    msgType = fields[1]
    fromId = int(fields[2]) if len(fields) > 2 else None
    toId = int(fields[3]) if len(fields) > 3 else None

    if msgType == 'F':
        followers[toId].append(fromId)
        users[toId].transport.write(message)
    elif msgType == 'U':
        if fromId in followers[toId]:
            followers[toId].remove(fromId)
    elif msgType == 'B':
        for user in users:
            user.transport.write(message)
    elif msgType == 'P':
        users[toId].transport.write(message)
    elif msgType == 'S':
        if followers[fromId]:
            for follower in followers[fromId]:
                users[follower].transport.write(message)
    else:
        print "ERROR: unhandled message type on message %s" % message
        pass

def blockingEventDispatch(events, nextEvent):
    try:
        if nextEvent in events:
            messageDispatcher(events[nextEvent])
            nextEvent = nextEvent + 1
    except KeyError:
        print "Error for %s : %s processing" % nextEvent, events[nextEvent]
        pass   # should never get here with the if above

if __name__ == '__main__':
    events = {}     # store all events here, keep full string, key is sequence #
    users = {}      # store all UserProtocol objects here, to write to later
    followers = {}  # key is userID, value is list of followers {1: [3, 7], 2: [9]...}

    delimiter = '\n'
    separator = '|'

    nextEvent = 1   # just a dumb counter

    eventSourceFactory = EventFactory()
    eventSourceFactory.protocol = EventProtocol

    userClientsFactory = Factory()
    userClientsFactory.protocol = UserProtocol
    userClientsFactory.clients = []

    try:
        LoopingCall(blockingEventDispatch, events, nextEvent).start(0.1)
    except Exception as err:
        print "ERROR starting looping call: %s" % err

    reactor.listenTCP(9090, eventSourceFactory)
    reactor.listenTCP(9099, userClientsFactory)
    reactor.run()
