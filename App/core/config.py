from pydantic import BaseSettings, Field

#Placing config.py here for now, will later expand to load from .env for security

class Settings(BaseSettings):
    ROBOT_HOST: Field()
    ROBOT_PORT: Field()
    ROBOT_USER: Field()
    ROBOT_PASSWORD: Field()