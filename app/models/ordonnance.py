from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from ..core.database import Base


class Ordonnance(Base):
    __tablename__ = "ordonnances"

    id = Column(Integer, primary_key=True, index=True)
    rendez_vous_id = Column(
        Integer,
        ForeignKey("rendez_vous.id"),
        nullable=False,
        unique=True,
        index=True,
    )
    patient_id = Column(Integer, ForeignKey("patients.id"), nullable=False, index=True)
    docteur_id = Column(Integer, ForeignKey("docteurs.id"), nullable=False, index=True)
    diagnostic = Column(Text, nullable=True)
    instructions = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    rendez_vous = relationship("RendezVous")
    patient = relationship("Patient")
    docteur = relationship("Docteur")
    medicaments = relationship(
        "OrdonnanceMedicament",
        back_populates="ordonnance",
        cascade="all, delete-orphan",
        order_by="OrdonnanceMedicament.id",
    )


class OrdonnanceMedicament(Base):
    __tablename__ = "ordonnance_medicaments"

    id = Column(Integer, primary_key=True, index=True)
    ordonnance_id = Column(
        Integer,
        ForeignKey("ordonnances.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    nom = Column(String(255), nullable=False)
    dosage = Column(String(100), nullable=False)
    posologie = Column(String(255), nullable=False)
    duree = Column(String(100), nullable=False)
    quantite = Column(Integer, nullable=True)
    instructions = Column(Text, nullable=True)

    ordonnance = relationship("Ordonnance", back_populates="medicaments")
