import calendar
from datetime import date, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.subscription import Subscription, SubscriptionStatus


def add_billing_interval(value: date, interval: str) -> date:
    if interval == "DAILY":
        return value + timedelta(days=1)
    if interval == "WEEKLY":
        return value + timedelta(weeks=1)
    if interval == "MONTHLY":
        month = value.month + 1
        year = value.year + (month - 1) // 12
        month = (month - 1) % 12 + 1
        return value.replace(year=year, month=month, day=min(value.day, calendar.monthrange(year, month)[1]))
    if interval == "YEARLY":
        try:
            return value.replace(year=value.year + 1)
        except ValueError:
            return value.replace(year=value.year + 1, day=28)
    raise ValueError(f"Unsupported billing interval: {interval}")


def process_due_subscriptions(db: Session, today: date | None = None) -> int:
    today = today or date.today()
    processed = 0
    subscriptions = db.scalars(
        select(Subscription).where(
            Subscription.status == SubscriptionStatus.ACTIVE,
            Subscription.next_billing_date.is_not(None),
            Subscription.next_billing_date <= today,
        ).with_for_update()
    ).all()
    for subscription in subscriptions:
        if subscription.end_date and subscription.end_date < today:
            subscription.status = SubscriptionStatus.CLOSED
            subscription.next_billing_date = None
        elif not all(line.renewal_allowed for line in subscription.lines):
            subscription.status = SubscriptionStatus.CLOSED
            subscription.next_billing_date = None
        else:
            subscription.last_billing_date = subscription.next_billing_date
            subscription.next_billing_date = add_billing_interval(
                subscription.next_billing_date, subscription.billing_interval
            )
            if subscription.end_date and subscription.next_billing_date > subscription.end_date:
                subscription.status = SubscriptionStatus.CLOSED
                subscription.next_billing_date = None
        processed += 1
    db.commit()
    return processed
