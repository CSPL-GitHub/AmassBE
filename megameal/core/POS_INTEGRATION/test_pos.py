

from core.POS_INTEGRATION.abstract_pos_integration import AbstractPOSIntegration


class TestIntegration(AbstractPOSIntegration):

    def pushProducts(self,VendorId,response):
        pass
    
    def pullProducts(VendorId):
        print(f"Ping pull products {VendorId=}")
        pass