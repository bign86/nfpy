#
# Interactive Brokers Downloader
# Downloads data from Interactive Brokers API
#

from ibapi.wrapper import EWrapper
from ibapi.client import EClient
from ibapi.contract import Contract


class IBAppFundamentals(EWrapper, EClient):

    def __init__(self):
        EClient.__init__(self, self)
        self.firstReqId = 1001  # remember starting id
        self.contracts = {}  # keep in dict so you can lookup
        self.contNumber = self.firstReqId
        self._data = None

    @property
    def return_data(self) -> str:
        return self._data

    # def addContracts(self, cont):
    #    self.contracts[self.contNumber] = cont  # add to dict using 8001 first time
    #    self.contNumber += 1  # next id will be 1002 etc.

    def addContracts(self, p: list, ccy: str):
        contract = Contract()
        contract.symbol = p[0]
        contract.currency = ccy
        contract.secType = 'STK'
        contract.exchange = 'SMART'
        contract.primaryExchange = p[1]
        # print("Contract: ", contract)

        self.contracts[self.contNumber] = contract  # add to dict using 8001 first time
        self.contNumber += 1  # next id will be 1002 etc.

    def nextValidId(self, orderId: int):
        # now you are connected, ask for data, no need for sleeps
        # this isn't the only way to know the api is started but it's what IB recommends
        self.contNumber = self.firstReqId  # start with first reqId
        self.getNextData()

    def error(self, reqId, errorCode, errorString):
        print("Error: ", reqId, "", errorCode, "", errorString)

        # if there was an error in one of your requests, just continue with next id
        if reqId > 0 and self.contracts.get(self.contNumber):
            # err in reqFundametalData based on reqid existing in map
            print('err in', self.contracts[reqId].symbol)
            self.getNextData()  # try next one

    def fundamentalData(self, reqId, fundamental_data):
        # note no need for globals, we have a dict of contracts
        self._data = fundamental_data
        self.getNextData()  # finished on request see if there are more

    def getNextData(self):
        if self.contracts.get(self.contNumber):  # means a contract exists
            # so req data
            self.reqFundamentalData(self.contNumber,
                                    self.contracts[self.contNumber],
                                    "ReportsFinStatements", [])
            self.contNumber += 1  # now get ready for next request
        else:  # means no more sequentially numbered contracts
            self.disconnect()  # just exit
