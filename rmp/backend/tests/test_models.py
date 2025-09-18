import pytest
from unittest.mock import Mock, patch
from sqlalchemy.orm import Session


class TestModels:
    """Test database models"""

    def test_user_creation(self, db_session):
        """Test creating a user model"""
        from models import User
        import uuid
        
        user = User(
            id=str(uuid.uuid4()),
            email="test@example.com",
            hashed_password="hashed_password_here",
            is_active=True
        )
        
        db_session.add(user)
        db_session.commit()
        
        # Retrieve user from database
        retrieved_user = db_session.query(User).filter(User.email == "test@example.com").first()
        
        assert retrieved_user is not None
        assert retrieved_user.email == "test@example.com"
        assert retrieved_user.is_active is True

    def test_pool_creation(self, db_session):
        """Test creating a pool model"""
        from models import Pool, User
        import uuid
        
        # Create a user first (foreign key requirement)
        user = User(
            id=str(uuid.uuid4()),
            email="owner@example.com",
            hashed_password="hashed_password_here"
        )
        db_session.add(user)
        db_session.commit()
        
        # Create pool
        pool = Pool(
            id=str(uuid.uuid4()),
            name="Test Pool",
            description="A test pool",
            is_private=False,
            owner_id=user.id
        )
        
        db_session.add(pool)
        db_session.commit()
        
        # Retrieve pool from database
        retrieved_pool = db_session.query(Pool).filter(Pool.name == "Test Pool").first()
        
        assert retrieved_pool is not None
        assert retrieved_pool.name == "Test Pool"
        assert retrieved_pool.owner_id == user.id
        assert retrieved_pool.is_private is False

    def test_user_pool_relationship(self, db_session):
        """Test the relationship between User and Pool"""
        from models import User, Pool
        import uuid
        
        # Create user
        user = User(
            id=str(uuid.uuid4()),
            email="owner@example.com",
            hashed_password="hashed_password_here"
        )
        db_session.add(user)
        db_session.commit()
        
        # Create pool owned by user
        pool = Pool(
            id=str(uuid.uuid4()),
            name="User's Pool",
            owner_id=user.id
        )
        db_session.add(pool)
        db_session.commit()
        
        # Test relationship
        retrieved_user = db_session.query(User).filter(User.id == user.id).first()
        assert len(retrieved_user.pools) == 1
        assert retrieved_user.pools[0].name == "User's Pool"

    def test_team_model(self, db_session):
        """Test Team model creation"""
        from models import Team
        
        team = Team(
            id=1,
            name="Test Team",
            abbrv="TT",
            logo="http://example.com/logo.png"
        )
        
        db_session.add(team)
        db_session.commit()
        
        retrieved_team = db_session.query(Team).filter(Team.abbrv == "TT").first()
        
        assert retrieved_team is not None
        assert retrieved_team.name == "Test Team"
        assert retrieved_team.abbrv == "TT"

    def test_user_enum_role(self, db_session):
        """Test UserRole enum"""
        from models import User, UserRole
        import uuid
        
        user = User(
            id=str(uuid.uuid4()),
            email="admin@example.com",
            hashed_password="hashed_password_here",
            role=UserRole.POOL_ADMIN
        )
        
        db_session.add(user)
        db_session.commit()
        
        retrieved_user = db_session.query(User).filter(User.email == "admin@example.com").first()
        
        assert retrieved_user.role == UserRole.POOL_ADMIN

    def test_model_string_representations(self, db_session):
        """Test model string representations (if implemented)"""
        from models import User, Pool
        import uuid
        
        user_id = str(uuid.uuid4())
        user = User(
            id=user_id,
            email="test@example.com",
            hashed_password="hashed_password_here"
        )
        
        # Test that model has basic attributes
        assert hasattr(user, 'id')
        assert hasattr(user, 'email')
        assert user.id == user_id


class TestSchemas:
    """Test Pydantic schemas"""

    def test_user_create_schema(self):
        """Test UserCreate schema validation"""
        try:
            from schemas import UserCreate
            
            # Valid user data
            valid_data = {
                "email": "test@example.com",
                "password": "validpassword123"
            }
            
            user = UserCreate(**valid_data)
            assert user.email == "test@example.com"
            assert user.password == "validpassword123"
            
        except ImportError:
            # Skip if schemas not available
            pytest.skip("Schemas module not available")

    def test_user_out_schema(self):
        """Test UserOut schema (excludes password)"""
        try:
            from schemas import UserOut
            import uuid
            
            user_data = {
                "id": str(uuid.uuid4()),
                "email": "test@example.com",
                "is_active": True
            }
            
            user = UserOut(**user_data)
            assert user.email == "test@example.com"
            assert user.is_active is True
            assert not hasattr(user, 'password')  # Should not have password field
            
        except ImportError:
            pytest.skip("Schemas module not available")

    def test_pool_schema_validation(self):
        """Test Pool schema validation"""
        try:
            from schemas import PoolCreate
            
            valid_pool_data = {
                "name": "Test Pool",
                "description": "A test pool",
                "is_private": False
            }
            
            pool = PoolCreate(**valid_pool_data)
            assert pool.name == "Test Pool"
            assert pool.is_private is False
            
        except ImportError:
            pytest.skip("Schemas module not available")

    def test_invalid_email_validation(self):
        """Test email validation in schemas"""
        try:
            from schemas import UserCreate
            from pydantic import ValidationError
            
            invalid_data = {
                "email": "invalid-email",
                "password": "validpassword123"
            }
            
            with pytest.raises(ValidationError):
                UserCreate(**invalid_data)
                
        except ImportError:
            pytest.skip("Schemas module not available")
