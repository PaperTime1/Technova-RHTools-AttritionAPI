"""Modèles SQLAlchemy pour PostgreSQL."""

from sqlalchemy import Column, Integer, Float, String, DateTime, JSON, func
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


class Employee(Base):
    """Table des employés (dataset complet)."""

    __tablename__ = "employees"

    id = Column(Integer, primary_key=True, autoincrement=True)
    age = Column(Integer, nullable=False)
    genre = Column(String(1), nullable=False)
    revenu_mensuel = Column(Float, nullable=False)
    statut_marital = Column(String(50), nullable=False)
    poste = Column(String(100), nullable=False)
    departement = Column(String(100))
    nombre_experiences_precedentes = Column(Integer)
    annee_experience_totale = Column(Integer)
    annees_dans_l_entreprise = Column(Integer)
    heure_supplementaires = Column(String(3))
    satisfaction_employee_environnement = Column(Integer)
    satisfaction_employee_nature_travail = Column(Integer)
    satisfaction_employee_equipe = Column(Integer)
    satisfaction_employee_equilibre_pro_perso = Column(Integer)
    note_evaluation_precedente = Column(Integer)
    augementation_salaire_precedente = Column(Float)
    nombre_participation_pee = Column(Integer)
    nb_formations_suivies = Column(Integer)
    distance_domicile_travail = Column(Integer)
    niveau_education = Column(Integer)
    domaine_etude = Column(String(100))
    frequence_deplacement = Column(String(50))
    annees_depuis_la_derniere_promotion = Column(Integer)
    attrition = Column(Integer, comment="0=resté, 1=parti")


class PredictionLogDB(Base):
    """Table de logs des prédictions (traçabilité des inputs/outputs)."""

    __tablename__ = "prediction_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    input_data = Column(JSON, nullable=False, comment="Données brutes envoyées à l'API")
    probability = Column(Float, nullable=False, comment="Probabilité de départ")
    prediction = Column(Integer, nullable=False, comment="0=resté, 1=parti")
    risk_level = Column(String(20), nullable=False)
    threshold_used = Column(Float, nullable=False)
