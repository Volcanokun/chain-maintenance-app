"""アプリケーション設定。環境変数から読み込む。"""

from urllib.parse import quote_plus

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """環境変数ベースの設定クラス。

    .envファイルまたはOS環境変数から自動的に値を読み込む。
    Pydanticによって型検証される。
    """

    # ECS が Secrets Manager から個別に注入する DB 接続パラメータ
    # ローカル開発時は未設定のまま → database_url のデフォルト（SQLite）を使用
    db_host: str = ""
    db_port: int = 5432
    db_name: str = ""
    db_user: str = ""
    db_password: str = ""

    # DB接続URL。db_host が設定されている場合は model_validator が上書きする。
    # ローカル開発デフォルト: SQLite
    database_url: str = "sqlite:///./dev.db"

    # アプリ動作モード
    app_env: str = "development"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",  # 未定義の環境変数は無視
    )

    @model_validator(mode="after")
    def assemble_db_url(self) -> "Settings":
        """DB_HOST が注入されている場合は PostgreSQL URL を組み立てる。"""
        if self.db_host:
            self.database_url = (
                f"postgresql+psycopg2://{self.db_user}:{quote_plus(self.db_password)}"
                f"@{self.db_host}:{self.db_port}/{self.db_name}"
                "?sslmode=require"
            )
        return self


settings = Settings()
