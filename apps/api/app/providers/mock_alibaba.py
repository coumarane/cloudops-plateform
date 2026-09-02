from app.data.inventory import MOCK_INVENTORY
from app.providers.filtering import FilteringAdapter


class MockAlibabaAdapter(FilteringAdapter):
    def __init__(self) -> None:
        super().__init__("Alibaba", MOCK_INVENTORY)
