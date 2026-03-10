import time

from ipywidgets import interact_manual, widgets

from massi.agents.interfaces import PromptClient


class JupyterTextWidgetIOPromptClient(PromptClient):
    def prompt_user(self, queries=[], prelude=[]):
        for msg in prelude:
            print(msg)
        container = []
        for i, q in enumerate(queries):
            ui = interact_manual(
                lambda **kwargs: container.extend(kwargs.values()),
                **{
                    f"q_{i}": widgets.Textarea(
                        description=q, style={"description_width": "initial"}
                    )
                },
            )

            while len(container) < i + 1:
                time.sleep(0.1)

            for child in ui.widget.children:
                child.disabled = True

        return container
