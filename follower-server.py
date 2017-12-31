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
                events[int(sequence)] = event.decode('utf-8')
            except:
                pass    # bad event?


class UserProtocol(Protocol):
    # make sure user clients don't time out waiting for events
    def connectionMade(self):
        try:
            self.transport.setTcpKeepAlive(1)
        except AttributeError: pass

    # only data received from user should be userId
    def dataReceived(self, data):
        userId = data.strip(delimiter)
        users[userId] = self
        followers[userId] = []

    def sendUserMessage(self, data):
        self.transport.write(data)

FOLLOW    = 'F'
UNFOLLOW  = 'U'
BROADCAST = 'B'
PRIVATE   = 'P'
STATUS    = 'S'

def messageDispatcher(message):
    fields = message.split(separator)

    # case statement on message type
    try:
        if fields[1] == FOLLOW:
            followers[fields[3]].append(fields[2])
            users[int(fields[3])].transport.write(message)
        elif fields[1] == UNFOLLOW:
            try:
                unfollowID = followers[int(fields[3])].index(int(fields[2]))
                followers[int(fields[3])].remove(unfollowID)
            except ValueError:
                print "ERROR: can't unfollow before following with message: %s" % message
                pass
        elif fields[1] == BROADCAST:
            for user in users:
                user.transport.write(message)
        elif fields[1] == PRIVATE:
            try:
                users[int(fields[3])].transport.write(message)
            except IndexError:
                print "ERROR: no recipient for private message %s" % message
                pass
        elif fields[1] == STATUS:
            for follower in followers[int(fields[2])]:
                users[follower].transport.write(message)
        else:
            print "ERROR: unhandled message type on message %s" % message
            pass
    except IndexError:
        print "ERROR: no message type found on message %s" % message
        pass

def blockingEventDispatch():
#    try:
#        message = events[eventSourceFactory.nextEvent]
#        messageDispatcher(events[eventSourceFactory.nextEvent])
#        print "processed event: %s" % message
#        eventSourceFactory.nextEvent = eventSourceFactory.nextEvent + 1
#    except KeyError:
#        pass
    try:
        message = events[nextEvent]
        messageDispatcher(events[nextEvent])
        print "processed event: %s" % message
        nextEvent = nextEvent + 1
    except KeyError:
        pass

if __name__ == '__main__':
    events = {}     # store all events here, keep full string, key is sequence #
    users = {}      # store all UserProtocol objects here, to write to later
    followers = {}  # key is userID, value is list of followers {1: [3, 7], 2: [9]...}

    delimiter = '\n'
    separator = '|'

    nextEvent = 1

    eventSourceFactory = EventFactory()
    eventSourceFactory.protocol = EventProtocol

    userClientsFactory = Factory()
    userClientsFactory.protocol = UserProtocol
    userClientsFactory.clients = []

    try:
        lc = LoopingCall(blockingEventDispatch)
        lc.start(0.1)
    except Exception as err:
        print "ERROR starting looping call: %s" % err

    reactor.listenTCP(9090, eventSourceFactory)
    reactor.listenTCP(9099, userClientsFactory)
    reactor.run()
