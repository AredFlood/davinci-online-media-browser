from __future__ import annotations

from dataclasses import dataclass

from ..config import LicensePolicy
from ..models import Asset


# (value, label) pairs for the UI license filter dropdown.
LICENSE_FILTERS: list[tuple[str, str]] = [
    ("all", "全部授权"),
    ("commercial", "仅商用可用"),
    ("free", "仅免署名 / CC0"),
    ("attribution", "需要署名"),
]


def filter_assets_by_license(assets: list[Asset], mode: str) -> list[Asset]:
    """Return the subset of ``assets`` matching a UI license filter ``mode``."""
    if mode == "commercial":
        return [asset for asset in assets if not asset.is_non_commercial]
    if mode == "free":
        return [asset for asset in assets if asset.is_attribution_free]
    if mode == "attribution":
        return [asset for asset in assets if asset.requires_attribution]
    return list(assets)


@dataclass(slots=True)
class LicenseDecision:
    allowed: bool
    requires_confirmation: bool
    title: str
    message: str


class LicenseService:
    def __init__(self, policy: LicensePolicy):
        self.policy = policy

    def evaluate(self, assets: list[Asset]) -> LicenseDecision:
        if not assets:
            return LicenseDecision(False, False, "No asset selected", "Select at least one asset to import.")

        non_commercial = [asset for asset in assets if asset.is_non_commercial]
        attribution = [asset for asset in assets if asset.requires_attribution]

        if non_commercial and not self.policy.allow_non_commercial:
            names = "\n".join(f"- {asset.display_title} ({asset.license_name})" for asset in non_commercial[:8])
            return LicenseDecision(
                allowed=False,
                requires_confirmation=False,
                title="版权风险：非商用素材已阻止",
                message=(
                    "以下素材标记为非商用授权，当前策略已阻止导入：\n"
                    f"{names}\n\n"
                    "只有在你的项目明确允许使用非商用素材时，才建议修改 license_policy.allow_non_commercial。"
                ),
            )

        if attribution and self.policy.require_attribution_confirmation:
            names = "\n".join(
                f"- {asset.display_title}: credit {asset.author or 'the original author'} ({asset.license_name})"
                for asset in attribution[:8]
            )
            return LicenseDecision(
                allowed=True,
                requires_confirmation=True,
                title="需要作者署名",
                message=(
                    "以下素材需要作者署名。插件会把署名信息写入 Resolve 素材元数据：\n"
                    f"{names}\n\n确认继续下载并导入？"
                ),
            )

        summary = "\n".join(
            f"- {asset.display_title}: {asset.license_name or 'License unspecified'} via {asset.source}"
            for asset in assets[:8]
        )
        return LicenseDecision(
            allowed=True,
            requires_confirmation=True,
            title="确认授权信息",
            message=(
                "下载并导入前请确认授权信息：\n"
                f"{summary}\n\n确认继续下载并导入？"
            ),
        )
