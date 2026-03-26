from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, ForeignKey, Text, Boolean
from sqlalchemy.orm import declarative_base, sessionmaker, relationship, scoped_session
from datetime import datetime
import os
import logging
import threading

Base = declarative_base()

class Transaction(Base):
    __tablename__ = 'transactions'

    id = Column(Integer, primary_key=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    type = Column(String(50), nullable=False)
    module = Column(String(100))
    amount = Column(Float, nullable=False)
    category = Column(String(100))
    asset_id = Column(Integer, ForeignKey('assets.id'), nullable=True)
    note = Column(Text)
    is_cancelled = Column(Boolean, default=False)
    
    asset = relationship("Asset", back_populates="transactions")

class Asset(Base):
    __tablename__ = 'assets'

    id = Column(Integer, primary_key=True)
    type = Column(String(50), nullable=False)
    name = Column(String(200), nullable=False)
    purchase_price = Column(Float, nullable=False)
    purchase_date = Column(DateTime, default=datetime.utcnow)
    current_value = Column(Float)
    depreciation_rate = Column(Float, default=0.0)
    is_active = Column(Boolean, default=True)
    
    transactions = relationship("Transaction", back_populates="asset")

class Profile(Base):
    __tablename__ = 'profiles'
    
    id = Column(Integer, primary_key=True)
    name = Column(String(200), unique=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    data = Column(Text)

class DatabaseManager:
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls, db_path=None):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._initialized = False
            return cls._instance

    def __init__(self, db_path=None):
        if self._initialized:
            return
            
        if db_path is None:
            import sys
            if getattr(sys, 'frozen', False):
                base_path = os.path.dirname(sys.executable)
            else:
                script_dir = os.path.dirname(os.path.abspath(__file__))
                cwd = os.getcwd()
                if os.path.exists(os.path.join(script_dir, "data.json")):
                    base_path = script_dir
                else:
                    base_path = cwd
            local_data = os.path.join(base_path, "data.json")
            if os.path.exists(local_data):
                data_dir = base_path
            else:
                data_dir = os.path.join(os.getenv("APPDATA"), "MoneyTracker")
                os.makedirs(data_dir, exist_ok=True)
            db_path = os.path.join(data_dir, "data.db")
            
        self.engine = create_engine(
            f"sqlite:///{db_path}",
            connect_args={"check_same_thread": False}
        )
        Base.metadata.create_all(self.engine)
        session_factory = sessionmaker(bind=self.engine)
        self.Session = scoped_session(session_factory)
        self._initialized = True
        self._session_lock = threading.Lock()

    def get_session(self):
        return self.Session()

    def add_transaction(self, type, amount, module=None, category=None, asset_id=None, note=None):
        session = self.Session()
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
        session = self.Session()
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
        session = self.Session()
        try:
            return session.query(Transaction).order_by(Transaction.timestamp.desc()).limit(limit).offset(offset).all()
        finally:
            session.close()

    def add_asset(self, type, name, purchase_price, depreciation_rate=0.0):
        session = self.Session()
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
        session = self.Session()
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
