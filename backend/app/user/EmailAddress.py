class EmailAddress(BaseModel):
    address: str
    alias: str

    def __str__(self):
        return f"EmailAddress(address={self.address}, alias={self.alias})"
    
    def get_address(self):
        return self.address
    
    def get_alias(self):
        return self.alias
    
