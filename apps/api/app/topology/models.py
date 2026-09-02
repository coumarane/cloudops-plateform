from __future__ import annotations

from dataclasses import dataclass


def environment_slug(environment: str) -> str:
    return "int-tst" if environment == "INT/TST" else environment.lower()


def environment_scope_id(account_alias: str, environment: str) -> str:
    return f"{account_alias}-{environment_slug(environment)}"


@dataclass(frozen=True)
class AccountBinding:
    id: str
    provider: str
    logical_region: str
    cloud_region: str
    alias: str
    account_id: str | None
    role_arn: str | None
    external_id: str | None
    account_class: str
    readonly: bool
    environments: tuple[str, ...]
    session_name: str
    cluster_environment_tag: str
    profile: str | None
    config_secret_arn: str | None

    def connection_config(self):
        from app.providers.aws.models import AwsConnectionConfig

        return AwsConnectionConfig(
            cloud_region=self.cloud_region,
            account_id=self.account_id,
            role_arn=self.role_arn,
            external_id=self.external_id,
            session_name=self.session_name,
            profile=self.profile,
            config_secret_arn=self.config_secret_arn,
            platform_region=self.logical_region,
            environment=self.environments[0] if self.environments else "",
            account_alias=self.alias,
            cluster_environment_tag=self.cluster_environment_tag,
        )

    def environment_ids(self) -> dict[str, str]:
        return {environment: environment_scope_id(self.alias, environment) for environment in self.environments}


@dataclass(frozen=True)
class EnvironmentBinding:
    id: str
    provider: str
    logical_region: str
    cloud_region: str
    account_id: str | None
    account_alias: str
    role_arn: str | None
    environment: str
    account_class: str
    readonly: bool

    def connection_config(self, account: AccountBinding):
        config = account.connection_config()
        from app.providers.aws.models import AwsConnectionConfig

        return AwsConnectionConfig(
            cloud_region=config.cloud_region,
            account_id=config.account_id,
            role_arn=config.role_arn,
            external_id=config.external_id,
            session_name=config.session_name,
            profile=config.profile,
            config_secret_arn=config.config_secret_arn,
            platform_region=config.platform_region,
            environment=self.environment,
            account_alias=config.account_alias,
            cluster_environment_tag=config.cluster_environment_tag,
        )


@dataclass(frozen=True)
class AwsTopology:
    accounts: tuple[AccountBinding, ...]
    scan_concurrency: int

    def environments(self) -> list[EnvironmentBinding]:
        rows: list[EnvironmentBinding] = []
        for account in self.accounts:
            for environment in account.environments:
                rows.append(
                    EnvironmentBinding(
                        id=environment_scope_id(account.alias, environment),
                        provider=account.provider,
                        logical_region=account.logical_region,
                        cloud_region=account.cloud_region,
                        account_id=account.account_id,
                        account_alias=account.alias,
                        role_arn=account.role_arn,
                        environment=environment,
                        account_class=account.account_class,
                        readonly=account.readonly or environment == "PRD",
                    )
                )
        return rows

    def account_by_alias(self, alias: str) -> AccountBinding | None:
        return next((item for item in self.accounts if item.alias == alias), None)
