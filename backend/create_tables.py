from app.database.session import engine
from app.database.base import Base
from app.users.models import User

Base.metadata.create_all(bind=engine)

print("✅ Tables created successfully")
