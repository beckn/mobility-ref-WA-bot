from pydantic import BaseSettings


class Settings(BaseSettings):
    collections = [
        "job",
        "msgcampaigns",
        "transactions",
        "response",
        "usercampaigns"
    ]


settings= Settings()