"""Modèle de données SQLAlchemy (PostgreSQL).

Quatre tables :
- employees            : dataset de référence (1 470 employés du P4) ;
- api_clients          : clients autorisés, clé d'API stockée hachée, rôle ;
- prediction_requests  : TOUTE requête reçue sur /predict (payload brut, appelant,
                         statut, latence) — y compris les requêtes rejetées ou en erreur ;
- predictions          : sortie du modèle, en relation 1:1 avec la requête qui l'a produite,
                         avec la version du modèle et le seuil utilisés.

L'intégrité est garantie par le SGBD (clés étrangères, CHECK, NOT NULL, UNIQUE),
pas seulement par l'application.
"""

from datetime import datetime

from sqlalchemy import (
    JSON,
    CheckConstraint,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    SmallInteger,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

# JSONB sous PostgreSQL (indexable, binaire), JSON générique ailleurs (SQLite en test local)
JSONType = JSON().with_variant(JSONB(), "postgresql")


class Base(DeclarativeBase):
    pass


class Employee(Base):
    """Dataset de référence : un employé TechNova (jointure SIRH + évaluations + sondage)."""

    __tablename__ = "employees"
    __table_args__ = (
        CheckConstraint("age BETWEEN 18 AND 70", name="ck_employees_age"),
        CheckConstraint("genre IN ('M', 'F')", name="ck_employees_genre"),
        CheckConstraint("revenu_mensuel >= 0", name="ck_employees_revenu"),
        CheckConstraint("heure_supplementaires IN ('Oui', 'Non')", name="ck_employees_hs"),
        CheckConstraint("attrition IN (0, 1)", name="ck_employees_attrition"),
        CheckConstraint(
            "satisfaction_employee_environnement BETWEEN 1 AND 4", name="ck_employees_sat_env"
        ),
    )

    # Identifiant SIRH d'origine (id_employee), conservé pour la traçabilité
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=False)
    age: Mapped[int] = mapped_column(Integer, nullable=False)
    genre: Mapped[str] = mapped_column(String(1), nullable=False)
    revenu_mensuel: Mapped[float] = mapped_column(Float, nullable=False)
    statut_marital: Mapped[str] = mapped_column(String(50), nullable=False)
    poste: Mapped[str] = mapped_column(String(100), nullable=False)
    departement: Mapped[str | None] = mapped_column(String(100))
    nombre_experiences_precedentes: Mapped[int | None] = mapped_column(Integer)
    annee_experience_totale: Mapped[int | None] = mapped_column(Integer)
    annees_dans_l_entreprise: Mapped[int | None] = mapped_column(Integer)
    annees_dans_le_poste_actuel: Mapped[int | None] = mapped_column(Integer)
    heure_supplementaires: Mapped[str | None] = mapped_column(String(3))
    satisfaction_employee_environnement: Mapped[int | None] = mapped_column(SmallInteger)
    satisfaction_employee_nature_travail: Mapped[int | None] = mapped_column(SmallInteger)
    satisfaction_employee_equipe: Mapped[int | None] = mapped_column(SmallInteger)
    satisfaction_employee_equilibre_pro_perso: Mapped[int | None] = mapped_column(SmallInteger)
    note_evaluation_precedente: Mapped[int | None] = mapped_column(SmallInteger)
    note_evaluation_actuelle: Mapped[int | None] = mapped_column(SmallInteger)
    niveau_hierarchique_poste: Mapped[int | None] = mapped_column(SmallInteger)
    augementation_salaire_precedente: Mapped[float | None] = mapped_column(Float)
    nombre_participation_pee: Mapped[int | None] = mapped_column(Integer)
    nb_formations_suivies: Mapped[int | None] = mapped_column(Integer)
    distance_domicile_travail: Mapped[int | None] = mapped_column(Integer)
    niveau_education: Mapped[int | None] = mapped_column(SmallInteger)
    domaine_etude: Mapped[str | None] = mapped_column(String(100))
    frequence_deplacement: Mapped[str | None] = mapped_column(String(50))
    annees_depuis_la_derniere_promotion: Mapped[int | None] = mapped_column(Integer)
    annes_sous_responsable_actuel: Mapped[int | None] = mapped_column(Integer)
    attrition: Mapped[int] = mapped_column(SmallInteger, nullable=False, comment="0=resté, 1=parti")

    requests: Mapped[list["PredictionRequest"]] = relationship(back_populates="employee")


class ApiClient(Base):
    """Client autorisé à appeler l'API. La clé n'est jamais stockée en clair."""

    __tablename__ = "api_clients"
    __table_args__ = (CheckConstraint("role IN ('predict', 'admin')", name="ck_api_clients_role"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    key_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)  # SHA-256 hex
    role: Mapped[str] = mapped_column(String(20), nullable=False, default="predict")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    requests: Mapped[list["PredictionRequest"]] = relationship(back_populates="client")


class PredictionRequest(Base):
    """Une requête reçue sur /predict : l'input exact, qui l'a envoyée, et son issue."""

    __tablename__ = "prediction_requests"
    __table_args__ = (
        CheckConstraint(
            "status IN ('success', 'rejected', 'error')", name="ck_prediction_requests_status"
        ),
        Index("ix_prediction_requests_created_at", "created_at"),
        Index("ix_prediction_requests_client_id", "client_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    client_id: Mapped[int | None] = mapped_column(ForeignKey("api_clients.id", ondelete="SET NULL"))
    employee_id: Mapped[int | None] = mapped_column(
        ForeignKey("employees.id", ondelete="SET NULL"),
        comment="Renseigné si la prédiction porte sur un employé connu",
    )
    payload: Mapped[dict] = mapped_column(JSONType, nullable=False, comment="Input brut reçu")
    status: Mapped[str] = mapped_column(String(10), nullable=False)
    error_detail: Mapped[str | None] = mapped_column(Text)
    latency_ms: Mapped[float | None] = mapped_column(Float)

    client: Mapped[ApiClient | None] = relationship(back_populates="requests")
    employee: Mapped[Employee | None] = relationship(back_populates="requests")
    prediction: Mapped["Prediction | None"] = relationship(
        back_populates="request", uselist=False, cascade="all, delete-orphan"
    )


class Prediction(Base):
    """Sortie du modèle pour une requête réussie (relation 1:1)."""

    __tablename__ = "predictions"
    __table_args__ = (
        CheckConstraint("probability BETWEEN 0 AND 1", name="ck_predictions_probability"),
        CheckConstraint("predicted_label IN (0, 1)", name="ck_predictions_label"),
        CheckConstraint("threshold > 0 AND threshold < 1", name="ck_predictions_threshold"),
        Index("ix_predictions_model_version", "model_version"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    request_id: Mapped[int] = mapped_column(
        ForeignKey("prediction_requests.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    probability: Mapped[float] = mapped_column(Float, nullable=False)
    predicted_label: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    risk_level: Mapped[str] = mapped_column(String(20), nullable=False)
    threshold: Mapped[float] = mapped_column(Float, nullable=False)
    model_version: Mapped[str] = mapped_column(String(64), nullable=False)

    request: Mapped[PredictionRequest] = relationship(back_populates="prediction")
