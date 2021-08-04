class Command:
    def __init__(self, ):
        self.dict = {}
        self.trigger = False
        self.Reply = False
        self.Reply2 = False
        self.Emoji = False
        self.Image = False
        self.Help = False
    
    def __add__(self, ):
        pass

    def __call__(self):
        return tuple(self.dict.values)



    def addTrigger(self, trigger):
        self.dict["trigger"] = trigger
        self.trigger = True
    
    def addReply(self, reply):
        self.dict["reply"] = reply
        self.Reply = True
    
    def addReply2(self, reply):
        self.dict["reply"] = reply
        self.Reply2 = True
    
    def addEmoji(self, reply):
        self.dict["reply"] = reply
        self.Emoji = True
    
    def addImage(self, reply):
        self.dict["reply"] = reply
        self.Image = True
    
    def addHelp(self, reply):
        self.dict["reply"] = reply
        self.Help = True


# incomplete