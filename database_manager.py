from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, ForeignKey, Text, Boolean
from sqlalchemy.orm import declarative_base, sessionmaker, relationship
from datetime import datetime
import os
import logging

Base = declarative_base()

class Transaction(Base):
    __tablename__ = 'transactions'

    id = Column(Integer, primary_key=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    type = Column(String(50), nullable=False) # income, expense, transfer
    module = Column(String(100)) # fishing, car_rental, etc.
    amount = Column(Float, nullable=False)
    category = Column(String(100))
    asset_id = Column(Integer, ForeignKey('assets.id'), nullable=True)
    note = Column(Text)
    is_cancelled = Column(Boolean, default=False)
    
    asset = relationship("Asset", back_populates="transactions")

class Asset(Base):
    __tablename__ = 'assets'

    id = Column(Integer, primary_key=True)
    type = Column(String(50), nullable=False) # car, equipment, etc.
    name = Column(String(200), nullable=False)
    purchase_price = Column(Float, nullable=False)
    purchase_date = Column(DateTime, default=datetime.utcnow)
    current_value = Column(Float)
    depreciation_rate = Column(Float, default=0.0) # Annual depreciation rate
    is_active = Column(Boolean, default=True)
    
    transactions = relationship("Transaction", back_populates="asset")

class Profile(Base):
    __tablename__ = 'profiles'
    
    id = Column(Integer, primary_key=True)
    name = Column(String(200), unique=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    data = Column(Text) # JSON blob for miscellaneous data

class DatabaseManager:
    def __init__(self, db_path="data.db"):
        self.engine = create_engine(f"sqlite:///{db_path}")
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)

    def get_session(self):
        return self.Session()

    def add_transaction(self, type, amount, module=None, category=None, asset_id=None, note=None):
        session = self.get_session()
        try:
            tx = Transaction(
                type=type,
                amount=amount,
                module=module,
                category=category,
                asset_id=asset_id,
                note=note
            )
            session.add(tx)
            session.commit()
            return tx.id
        except Exception as e:
            session.rollback()
            logging.error(f"Error adding transaction: {e}")
            raise
        finally:
            session.close()

    def cancel_transaction(self, tx_id):
        session = self.get_session()
        try:
            tx = session.query(Transaction).filter_by(id=tx_id).first()
            if tx:
                tx.is_cancelled = True
                session.commit()
                return True
            return False
        except Exception as e:
            session.rollback()
            logging.error(f"Error cancelling transaction: {e}")
            raise
        finally:
            session.close()

    def get_transactions(self, limit=100, offset=0):
        session = self.get_session()
        try:
            return session.query(Transaction).order_by(Transaction.timestamp.desc()).limit(limit).offset(offset).all()
        finally:
            session.close()

    def add_asset(self, type, name, purchase_price, depreciation_rate=0.0):
        session = self.get_session()
        try:
            asset = Asset(
                type=type,
                name=name,
                purchase_price=purchase_price,
                current_value=purchase_price,
                depreciation_rate=depreciation_rate
            )
            session.add(asset)
            session.commit()
            return asset.id
        except Exception as e:
            session.rollback()
            logging.error(f"Error adding asset: {e}")
            raise
        finally:
            session.close()

    def update_asset_value(self, asset_id, new_value):
        session = self.get_session()
        try:
            asset = session.query(Asset).filter_by(id=asset_id).first()
            if asset:
                asset.current_value = new_value
                session.commit()
                return True
            return False
        except Exception as e:
            session.rollback()
            logging.error(f"Error updating asset value: {e}")
            raise
        finally:
            session.close()
