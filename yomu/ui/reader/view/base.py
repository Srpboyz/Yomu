from abc import ABC, ABCMeta, abstractmethod
from typing import Callable, TYPE_CHECKING

from PyQt6.QtCore import pyqtSignal, QPoint
from PyQt6.QtWidgets import QMenu, QWidget


if TYPE_CHECKING:
    from yomu.ui import ReaderWindow
    from yomu.ui.reader import Reader
    from yomu.ui.reader.page import PageView


class ViewMeta(type(QWidget), ABCMeta): ...


class BaseView(QWidget, ABC, metaclass=ViewMeta):
    """
    Abstract base class for reader view implementations.

    Provides common functionality for displaying and navigating pages in different view modes.
    Subclasses must implement page display, clearing, and point-based page lookup functionality.

    Attributes
    ----------
    name : str
        Human-readable name of the view mode, defaults to class name if not set.
    supports_zoom : bool
        Whether this view supports zoom in/out operations. Defaults to False.
    page_changed : pyqtSignal
        Signal emitted when the current page index changes, passing the new index.
    zoomed : pyqtSignal
        Signal emitted when a zoom operation occurs.
    reader : Reader
        Reference to the parent Reader instance managing this view.
    """

    name: str
    supports_zoom: bool = False

    page_changed = pyqtSignal(int)
    zoomed = pyqtSignal()

    def __init__(self, reader: Reader) -> None:
        """
        Initialize the BaseView with a reference to the parent Reader.

        Parameters
        ----------
        reader : Reader
            The Reader instance that manages this view's lifecycle and pages.
        """
        super().__init__(reader)
        self.reader = reader
        self._current_index = -1

    def __init_subclass__(cls) -> None:
        """
        Hook called when a subclass is created. Automatically sets the class name
        as the 'name' attribute if not explicitly defined by the subclass.

        This allows view subclasses to have a default human-readable name without
        requiring explicit assignment.
        """
        if not isinstance(getattr(cls, "name", None), str):
            cls.name = cls.__name__
        return super().__init_subclass__()

    window: Callable[[], ReaderWindow]

    @property
    def current_index(self) -> int:
        """
        Get the current page index (zero-based).

        Returns
        -------
        int
            The index of the currently displayed page. Returns -1 if no page is set.
        """
        return self._current_index

    @current_index.setter
    def current_index(self, index: int) -> None:
        """
        Set the current page index (zero-based).

        Delegates to the `set_current_index` method to allow subclass overrides
        of the page change logic.

        Parameters
        ----------
        index : int
            The page index to set.
        """
        self.set_current_index(index)

    def set_current_index(self, index: int) -> None:
        """
        Set the current page index and emit a change signal if the index changed.

        Subclasses should override this method to implement view-specific page update logic
        (e.g., refreshing displayed content, scroll position adjustments).

        Parameters
        ----------
        index : int
            The zero-based page index to navigate to.
        """
        if index != self._current_index:
            self._current_index = index
            self.page_changed.emit(index)

    page = current_index

    @property
    def page_count(self) -> int:
        """
        Get the total number of pages available in the current reader.

        Returns
        -------
        int
            The count of pages in the reader's page list.
        """
        return len(self.reader.pages)

    @abstractmethod
    def set_page_views(self, pages: list[PageView]) -> None:
        """
        Display a list of page views in this view.

        Subclasses must implement this to render the provided pages according to their specific layout strategy.

        Parameters
        ----------
        pages : list[PageView]
            A list of PageView objects to display.
        """

    @abstractmethod
    def clear(self) -> None:
        """
        Clear all pages from the view.

        Subclasses must implement this to perform cleanup of displayed pages.
        """

    def zoom_out(self) -> None:
        """
        Handle a zoom out request from the user.

        Only called if supports_zoom is True. Subclasses should override this
        to implement zoom out functionality and emit the zoomed signal when complete.
        """

    def zoom_in(self) -> None:
        """
        Handle a zoom in request from the user.

        Only called if supports_zoom is True. Subclasses should override this
        to implement zoom in functionality and emit the zoomed signal when complete.
        """

    @abstractmethod
    def page_at(self, pos: QPoint) -> PageView | None:
        """
        Retrieve the page view located at the given screen position.

        Used to determine which page the user clicked on when displaying context menus
        or handling other position-based interactions.

        Parameters
        ----------
        pos : QPoint
            The screen coordinates to check.

        Returns
        -------
        PageView | None
            The PageView at the given position, or None if no page exists at that location.
        """

    def context_menu(self) -> QMenu | None:
        """
        Build and return a context menu for view-specific actions.

        Called when the user right-clicks in the view. Subclasses can override
        to provide custom context menu options relevant to the view mode.

        Returns
        -------
        QMenu | None
            A QMenu with view-specific actions, or None to use default behavior.
        """

    def unload(self) -> None:
        """
        Clean up and reset the view when switching to a different view mode.

        Called before this view is replaced with another view. Subclasses should override
        to reset any state, disconnect signals, clear caches, or perform other cleanup
        needed when this view is no longer active.
        """
