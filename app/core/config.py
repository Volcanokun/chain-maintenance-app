"""アプリケーション設定。環境変数から読み込む。"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """環境変数ベースの設定クラス。

    .envファイルまたはOS環境変数から自動的に値を読み込む。
    Pydanticによって型検証される。
    """

    # DB接続URL。デフォルトはローカルSQLite。
    # Phase 2でPostgreSQLに切り替える際は.envでオーバーライドする。
    database_url: str = "sqlite:///./dev.db"

    # アプリ動作モード
    app_env: str = "development"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",  # 未定義の環境変数は無視
    )


settings = Settings()
