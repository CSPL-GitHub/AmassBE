from abc import ABC, abstractmethod

class AbstractPOSIntegration(ABC):
    @abstractmethod
    def pullProducts(VendorId):
        pass

    @abstractmethod
    def pushProducts(self,VendorId,response):
        pass

    @abstractmethod
    def openOrder(response):
        pass

    @abstractmethod
    def addLineItem(response):
        pass

    @abstractmethod
    def addModifier(response):
        pass

    @abstractmethod
    def applyDiscount(response):
        pass

    @abstractmethod
    def payBill(response):
        pass
    
    @abstractmethod
    def getOrder(response):
        pass
