from pydantic_settings import BaseSettings


class MCPSettings(BaseSettings):
    dspy_root: str = "."
    log_level: str = "INFO"

    class Config:
        env_prefix = "DSPSY_MCP_"


settings = MCPSettings()
