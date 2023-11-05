from pydantic import BaseModel

EVENT_ID = 0


class Event(BaseModel):
    id: int


class DeliveryRequestEvent(Event):
    load_weight: int
    origin_address: str
    destination_address: str

    @classmethod
    def create(
        cls, *, origin_address: str, destination_address: str, load_weight: int = 0
    ):
        global EVENT_ID
        id_ = EVENT_ID
        EVENT_ID += 1
        return cls(
            id=id_,
            load_weight=load_weight,
            origin_address=origin_address,
            destination_address=destination_address,
        )
