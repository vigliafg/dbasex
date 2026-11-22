"""Anteprima delle etichette: riusa la finestra Preview dei report (0.8 O7)."""

from __future__ import annotations

from PyQt6.QtWidgets import QWidget

from ..core.label_model import LabelSpec
from ..runtime.label_engine import render_labels_for_project
from .report_preview import ReportPreviewDialog


class LabelPreviewDialog(ReportPreviewDialog):
    """Preview, stampa e PDF di un foglio di etichette o di un mail merge."""

    DOC_LABEL = "Etichetta"

    def __init__(self, project, label, parent: QWidget | None = None) -> None:
        if isinstance(label, str):
            artifact = project.artifact("labels", label)
            if artifact is None:
                raise ValueError(f"Etichetta sconosciuta: {label}")
            label = LabelSpec.from_dict(artifact)
        super().__init__(project, label, parent)
        self.setWindowTitle(
            f"Preview etichette — {self.spec.title or self.spec.name}"
        )

    def build_pages(self):
        return render_labels_for_project(self.project, self.spec)


__all__ = ["LabelPreviewDialog"]
