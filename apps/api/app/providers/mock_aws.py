from app.data.inventory import MOCK_INVENTORY
from app.providers.filtering import FilteringAdapter


class MockAwsAdapter(FilteringAdapter):
    def __init__(self) -> None:
        super().__init__("AWS", MOCK_INVENTORY)
