from twisted.internet import reactor, threads
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
        followers[userId] = []

    def sendUserMessage(self, user, data):
        users[user].sendMessage(data)

FOLLOW    = 'F'
UNFOLLOW  = 'U'
BROADCAST = 'B'
PRIVATE   = 'P'
STATUS    = 'S'

def messageDispatcher(message):
    fields = message.split(separator)

    # case statement on message type
    if fields[1] == FOLLOW:
        followers[fields[3]].append(fields[2])
        users[fields[3]].sendUserMessage(message)
    elif fields[1] == UNFOLLOW:
        try:
            unfollowID = followers[fields[3]].index(fields[2])
            followers[fields[3]].remove(unfollowID)
        except ValueError:
            pass
    elif fields[1] == BROADCAST:
        for user in users:
            user.sendUserMessage(message)
    elif fields[1] == PRIVATE:
        users[fields[3]].sendUserMessage(message)
    elif fields[1] == STATUS:
        for follower in followers[field[2]]:
            users[follower].sendUserMessage(message)
    else:
        print "ERROR: unhandled message type"
        exit(-1)

# not exactly threadsafe, but only Follow and Unfollow are trying to change data
def blockingEventDispatch():
    import datetime
    nextEvent = 1
    while True:
        try:
            message = events[nextEvent]
            print "processing event %s" % str(nextEvent)
            messageDispatcher(events[nextEvent])
            nextEvent = nextEvent + 1
        except KeyError:
            pass

if __name__ == '__main__':
    events = {}     # store all events here, keep full string, key is sequence #
    users = {}      # store all UserProtocol objects here, to write to later
    followers = {}  # key is userID, value is list of followers {1: [3, 7], 2: [9]...}

    delimiter = '\n'
    separator = '|'

    event_source_factory = Factory()
    event_source_factory.protocol = EventProtocol

    user_clients_factory = Factory()
    user_clients_factory.protocol = UserProtocol

    reactor.listenTCP(9090, event_source_factory)
    reactor.listenTCP(9099, user_clients_factory)

    reactor.callFromThread(blockingEventDispatch)
    reactor.run()
