from napari_plugin_engine import napari_hook_implementation
from qtpy.QtWidgets import QWidget, QHBoxLayout, QPushButton, QLayout, QLabel, QTabWidget
from qtpy.QtWidgets import QSpacerItem, QSizePolicy
from qtpy.QtCore import QTimer
from magicgui import magic_factory
from napari_tools_menu import register_dock_widget

@register_dock_widget(menu="Visualization > Workflow Viewer")
class WorkflowWidget(QWidget):
    # your QWidget.__init__ can optionally request the napari viewer instance
    # in one of two ways:
    # 1. use a parameter called `napari_viewer`, as done here
    # 2. use a type annotation of 'napari.viewer.Viewer' for any parameter
    def __init__(self, napari_viewer):
        super().__init__()
        self.viewer = napari_viewer

        lbl_from_roots = QLabel("")
        lbl_from_leafs = QLabel("")

        tabs = QTabWidget()
        tabs.addTab(lbl_from_roots, "From source")
        tabs.addTab(lbl_from_leafs, "From target")

        self.setLayout(QHBoxLayout())
        self.layout().addWidget(tabs)
        verticalSpacer = QSpacerItem(20, 40, QSizePolicy.Minimum, QSizePolicy.Expanding)
        self.layout().addItem(verticalSpacer)


        self.timer = QTimer()
        self.timer.setInterval(500)

        @self.timer.timeout.connect
        def update_layer(*_):
            from ._workflow import WorkflowManager, _layer_invalid, _viewer_has_layer
            workflow = WorkflowManager.install(napari_viewer).workflow

            def build_output(list_of_items, func_to_follow, level=0):
                output = ""
                for i in list_of_items:
                    if _viewer_has_layer(self.viewer, i):
                        layer = self.viewer.layers[i]
                        if _layer_invalid(layer):
                            output = output + '<font color="#ff0000">'
                        else:
                            output = output + '<font color="#00ff00">'
                        output = output + ("   " * level) + "-> " + i + ""
                        output = output + '</font>\n'

                        output = output + build_output(func_to_follow(i), func_to_follow, level + 1)
                return "<html><pre>" + output + "</pre></html>"

            lbl_from_roots.setText(build_output(workflow.roots(), workflow.followers_of))
            lbl_from_leafs.setText(build_output(workflow.leafs(), workflow.sources_of))

        self.timer.start()


@napari_hook_implementation
def napari_experimental_provide_dock_widget():
    # you can return either a single widget, or a sequence of widgets
    return [WorkflowWidget]
