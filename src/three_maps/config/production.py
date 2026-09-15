from __future__ import annotations
from dataclasses import dataclass
import os

@dataclass(frozen=True)
class ProductionSettings:
    environment: str = os.getenv('THE_THREE_MAPS_ENV', 'development')
    database_path: str = os.getenv('THE_THREE_MAPS_DB_PATH', ':memory:')
    allowed_origins: tuple[str, ...] = tuple(x.strip() for x in os.getenv('THE_THREE_MAPS_ALLOWED_ORIGINS', '').split(',') if x.strip())
    rate_limit_per_minute: int = int(os.getenv('THE_THREE_MAPS_RATE_LIMIT_PER_MINUTE', '60'))
    max_body_bytes: int = int(os.getenv('THE_THREE_MAPS_MAX_BODY_BYTES', '1000000'))

    def validate(self) -> None:
        if self.rate_limit_per_minute < 1:
            raise ValueError('rate_limit_per_minute must be >= 1')
        if self.max_body_bytes < 1024:
            raise ValueError('max_body_bytes must be >= 1024')
        if self.environment == 'production' and not self.allowed_origins:
            raise ValueError('Explicit CORS origins are required in production')


def load_settings() -> ProductionSettings:
    s = ProductionSettings()
    s.validate()
    return s
