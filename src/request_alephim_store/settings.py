from pydantic import BaseSettings, Field


class Settings(BaseSettings):
    aleph_channel: str = "TEST"
    aleph_api_server: str = "https://api2.aleph.im"
    
    ethereum_incoming_enabled: bool = False
    ethereum_outgoing_enabled: bool = True
    ethereum_api_server: str = None
    ethereum_event_contract: str = "0x24A66AfdA3666FB0202f439708ECE45c8121a9bB"
    ethereum_pkey: str = ""
    ethereum_min_height: int = 8225148
    
    class Config:
        env_file = '.env'

settings = Settings()
