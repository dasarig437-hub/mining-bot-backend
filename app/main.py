from fastapi import FastAPI, Depends, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime, timedelta, timezone
import json

from .database import engine, Base, get_db
from .models import User
from .auth import validate_telegram_init_data

app = FastAPI()

# ---- CORS ----
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # tighten later
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---- STARTUP ----
@app.on_event("startup")
async def startup():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

# ---- AUTH DEPENDENCY ----
async def get_current_user(
    x_telegram_init_data: str = Header(None, alias="X-Telegram-Init-Data"),
    db: AsyncSession = Depends(get_db)
):
    if not x_telegram_init_data:
        raise HTTPException(status_code=401, detail="Missing Telegram data")

    try:
        data = validate_telegram_init_data(x_telegram_init_data)
        user_data = json.loads(data["user"])
        telegram_id = user_data["id"]
        username = user_data.get("username")

        start_param = data.get("start_param")
        referrer = int(start_param) if start_param and start_param.isdigit() else None

        result = await db.execute(
            select(User).where(User.telegram_id == telegram_id)
        )
        user = result.scalars().first()

        if not user:
            user = User(
                telegram_id=telegram_id,
                username=username,
                referred_by=referrer if referrer != telegram_id else None
            )
            db.add(user)
            await db.commit()
            await db.refresh(user)

        return user

    except Exception:
        raise HTTPException(status_code=403, detail="Invalid Telegram data")

# ---- ROUTES ----
@app.get("/me")
async def me(user: User = Depends(get_current_user)):
    return {
        "balance": user.balance,
        "energy": user.energy,
        "referrer": user.referred_by
    }

@app.post("/mine")
async def mine(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    if user.is_banned:
        raise HTTPException(403, "Banned")

    if user.energy <= 0:
        raise HTTPException(400, "No energy")

    now = datetime.now(timezone.utc)

    if user.last_active and (now - user.last_active) < timedelta(seconds=1):
        raise HTTPException(429, "Too fast")

    user.balance += 1
    user.energy -= 1
    user.last_active = now

    await db.commit()

    return {
        "balance": user.balance,
        "energy": user.energy
    }
@app.post("/refill")
async def refill_energy(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    if user.is_banned:
        raise HTTPException(403, "Banned")

    user.energy = 500
    await db.commit()

    return {
        "energy": user.energy
    }
