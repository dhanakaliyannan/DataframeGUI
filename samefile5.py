from PyQt5 import QtCore, QtGui, QtWidgets
import pandas
import numpy as np
from functools import partial
import operator


class MyDelegate(QtWidgets.QItemDelegate):

    def createEditor(self, parent, option, index):
        #if index.columns() == 2:
        return super(MyDelegate, self).createEditor(parent, option, index)
        #return None

    def setEditorData(self, editor, index):
        #if index.columns() == 2:
        # Gets display text if edit data hasn't been set
        text = index.data(QtCore.Qt.EditRole) or index.data(QtCore.Qt.DisplayRole)
        editor.setText(text)


class DataFrameModel(QtCore.QAbstractTableModel):
    # data model for a DataFrame class
    RawDataRole = 64    # Custom Role, http://qt-project.org/doc/qt-4.8/qt.html#ItemDataRole-enum
    RawIndexRole = 65
    def __init__(self):
        super(DataFrameModel, self).__init__()
        self._df = pandas.DataFrame()
        self._cols = self._df.columns
        self._orig_df = pandas.DataFrame()
        self._resort = lambda : None # Null resort functon

    def setDataFrame(self, dataFrame):
        #set or change pandas DataFrame to show
        self.df = dataFrame
        self.dfcol = self.df.columns
        self._orig_df = dataFrame

    @property
    def df(self):
        return self._df

    @df.setter
    def df(self, dataFrame):
        self.modelAboutToBeReset.emit()
        self._df = dataFrame
        self._cols = dataFrame.columns
        self.modelReset.emit()


    def headerData(self, section, orientation, role=QtCore.Qt.DisplayRole):
        if role != QtCore.Qt.DisplayRole:
            return None
        if orientation == QtCore.Qt.Horizontal:
            try:
                return self._cols[section] #'%s' % self.df.columns.tolist()[section]
            except (IndexError, ):
                return QtCore.QVariant()
        elif orientation == QtCore.Qt.Vertical:
            try:
                return section #'%s' % self.df.index.tolist()[section]
            except (IndexError, ):
                return QtCore.QVariant()

    def flags(self, index):
        defaults = super(DataFrameModel, self).flags(index)
        return defaults | QtCore.Qt.ItemIsEditable


    def setData(self, index, value, role):
        row = self.df.index[index.row()]
        col = self.df.columns[index.column()]
        if hasattr(value, 'toPyObject'):
            value = value.toPyObject()
        else:
            dtype = self.df[col].dtype
            if dtype != object:
                value = self.df.at[row, col] if value == '' else dtype.type(value)

        self.df.at[row, col] = value
        self._orig_df.at[row, col] = value
        self.dataChanged.emit(index, index)
        return True

    def data(self, index, role=QtCore.Qt.DisplayRole):
        if role = QtCore.Qt.DisplayRole:
            if not index.isValid():
                return QtCore.QVariant()
            data = self.df.iloc[index.row(), index.column()]
            if pandas.isnull(data):
                return  QtCore.QVariant()

            if role == QtCore.Qt.TextAlignmentRole:
                if type(self.df.iloc[index.row(), index.column()]) = np.float64:
                    return QtCore.Qt.AlignRight
                elif type(self.df.iloc[index.row(), index.column()]) = np.int16 or type(self.df.iloc[index.row(), index.column()]) = np.int32 or type(self.df.iloc[index.row(), index.column()]) = np.int64:
                    return QtCore.Qt.AlignCenter
                else:
                    return QtCore.Qt.AlignLeft
            else:
                return None


    def rowCount(self, index=QtCore.QModelIndex()):
        return self.df.shape[0]

    def columnCount(self, index=QtCore.QModelIndex()):
        return self.df.shape[1]


    def sort(self, col_ix, order = QtCore.Qt.AscendingOrder):
        if col_ix >= self.df.shape[1]:
            return
        self.layoutAboutToBeChanged.emit()
        ascending = True if order == QtCore.Qt.AscendingOrder else False
        self.df = self.df.sort_values(self.df.columns[col_ix], ascending=ascending)
        self.layoutChanged.emit()
        self._resort = partial(self.sort, col_ix, order)

    def filter(self, col_ix, needle):

        df = self.df
        col = df.columns[col_ix]

        # Create lowercase string version of column as series
        s_lower = df[col].astype('str').str.lower()
        # Make needle lower case too
        needle = str(needle).lower()
        # Actually filter
        self.df = df[s_lower.str.contains(str(needle))]
        # Resort
        self._resort()

    def filterIsIn(self, col_ix, include):

        df = self._orig_df
        col = self.df.columns[col_ix]
        # Convert to string
        s_col = df[col].astype('str')
        # Filter
        self.df = df[s_col.isin(include)]
        # Resort
        self._resort()


    def filterFunction(self, col_ix, function):

        df = self.df
        col = self.df.columns[col_ix]
        self.df = df[function(df[col])]
        # Resort
        self._resort()

    def reset(self):
        self.df = self._orig_df.copy()
        self._resort = lambda: None

class DynamicFilterLineEdit(QtWidgets.QLineEdit):
    # Filter textbox for a DataFrameTable"""
    def __init__(self, *args, **kwargs):
        self._always_dynamic = kwargs.pop('always_dynamic', False)
        super(DynamicFilterLineEdit, self).__init__(*args, **kwargs)
        self.col_to_filter = None
        self._orig_df = None
        self._host = None

    def bind_dataframewidget(self, host, col_ix):

        #Bind tihs DynamicFilterLineEdit to a DataFrameTable's column
        #Args:
        #    host (DataFrameWidget)
        #        Host to filter
        #    col_ix (int)
        #        Index of column of host to filter

        self.host = host
        self.col_to_filter = col_ix
        self.textChanged.connect(self._update_filter)

    @property
    def host(self):
        if self._host is None:
            raise RuntimeError("Must call bind_dataframewidget() "
                               "before use.")
        else:
            return self._host

    @host.setter
    def host(self, value):
        if not isinstance(value, DataFrameWidget):
            raise ValueError("Must bind to a DataFrameWidget, not %s" % value)
        else:
            self._host = value

    def _update_filter(self, text):
        col_ix = self.col_to_filter
        self.host.filter(col_ix, text)

class DynamicFilterMenuAction(QtWidgets.QWidgetAction):
    #Filter textbox in column-header right-click menu"""
    def __init__(self, parent, menu, col_ix):
        """Filter textbox in column right-click menu
        Args:
            parent (DataFrameWidget)
                Parent who owns the DataFrame to filter
            menu (QMenu)
                Menu object I am located on
            col_ix (int)
                Index of column used in pandas DataFrame we are to filter
        """
        super(DynamicFilterMenuAction, self).__init__(parent)
        # State
        self.parent_menu = menu
        # Build Widgets
        widget = QtWidgets.QWidget()
        layout = QtWidgets.QHBoxLayout()
        self.label = QtWidgets.QLabel('Filter')
        self.text_box = DynamicFilterLineEdit()
        self.text_box.bind_dataframewidget(self.parent(), col_ix)
        self.text_box.returnPressed.connect(self._close_menu)
        layout.addWidget(self.label)
        layout.addWidget(self.text_box)
        widget.setLayout(layout)
        self.setDefaultWidget(widget)

    def _close_menu(self):
        """Gracefully handle menu"""
        self.parent_menu.close()

class FilterListMenuWidget(QtWidgets.QWidgetAction):
    """Filter textbox in column-right click menu"""
    def __init__(self, parent, menu, col_ix):
        """Filter textbox in column right-click menu
        Args:
            parent (DataFrameWidget)
                Parent who owns the DataFrame to filter
            menu (QMenu)
                Menu object I am located on
            col_ix (int)
                Column index used in pandas DataFrame we are to filter
            label (str)
                Label in popup menu
        """
        super(FilterListMenuWidget, self).__init__(parent)

        # State
        self.menu = menu
        self.col_ix = col_ix
        # Build Widgets

        widget = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout()
        self.list = QtWidgets.QListWidget()
        self.list.setFixedHeight(200)
        layout.addWidget(self.list)
        widget.setLayout(layout)
        self.setDefaultWidget(widget)

        # Signals/slots
        self.list.itemChanged.connect(self.on_list_itemChanged)
        #self.parent().dataFrameChanged.connect(self._populate_list)
        self._populate_list(inital=True)

    def _populate_list(self, inital=False):
        self.list.clear()
        df = self.parent()._data_model._orig_df
        col = df.columns[self.col_ix]
        full_col = set(df[col])  # All Entries possible in this column
        disp_col = set(self.parent().df[col]) # Entries currently displayed

        def _build_item(item, state=None):
            i = QtWidgets.QListWidgetItem('%s' % item)
            i.setFlags(i.flags() | QtCore.Qt.ItemIsUserCheckable)
            if state is None:
                if item in disp_col:
                    state = QtCore.Qt.Checked
                else:
                    state = QtCore.Qt.Unchecked
            i.setCheckState(state)
            i.checkState()
            self.list.addItem(i)
            return i

        # Add a (Select All)
        if full_col == disp_col:
            select_all_state = QtCore.Qt.Checked
        else:
            select_all_state = QtCore.Qt.Unchecked
        self._action_select_all = _build_item('(Select All)', state=select_all_state)

        # Add filter items
        if inital:
            build_list = full_col
        else:
            build_list = disp_col
        for i in sorted(build_list):
            _build_item(i)

        # Add a (Blanks)
        # TODO



    def on_list_itemChanged(self, item):
        ###
        # Figure out what "select all" check-box state should be
        ###
        self.list.blockSignals(True)
        if item is self._action_select_all:
            # Handle "select all" item click
            if item.checkState() == QtCore.Qt.Checked:
                state = QtCore.Qt.Checked
            else:
                state = QtCore.Qt.Unchecked
            # Select/deselect all items

            for i in range(self.list.count()):
                if i is self._action_select_all: continue
                i = self.list.item(i)
                i.setCheckState(state)

        else:
            # Non "select all" item; figure out what "select all" should be
            if item.checkState() == QtCore.Qt.Unchecked:
                self._action_select_all.setCheckState(QtCore.Qt.Unchecked)
            else:
                # "select all" only checked if all other items are checked
                for i in range(self.list.count()):
                    i = self.list.item(i)
                    if i is self._action_select_all: continue
                    if i.checkState() == QtCore.Qt.Unchecked:
                        self._action_select_all.setCheckState(QtCore.Qt.Unchecked)
                        break
               else:
                    self._action_select_all.setCheckState(QtCore.Qt.Checked)
        self.list.blockSignals(False)

        ###
        # Filter dataframe according to list
        ###
        include = []
        for i in range(self.list.count()):
            i = self.list.item(i)
            if i is self._action_select_all: continue
            if i.checkState() == QtCore.Qt.Checked:
                include.append(str(i.text()))

        #self.parent().blockSignals(True)
        self.parent().filterIsIn(self.col_ix, include)
        #self.parent().blockSignals(False)
        #self.parent()._enable_widgeted_cells()

class QTableViewWidget(QtWidgets.QTableView):

    dataFrameChanged = QtCore.pyqtSignal()
    cellClicked = QtCore.pyqtSignal(int, int)
    viewResults = QtCore.pyqtSignal()

    def __init__(self):

        super(QTableViewWidget, self).__init__()
        self.defaultCSVFile = "temp.csv"
        self.viewIndex = 0


        # Set up view

        delegate = MyDelegate()
        self.setItemDelegate(delegate)


        self._data_model = DataFrameModel()
        self.setModel(self._data_model)
        # Signals/Slots

        self._data_model.modelReset.connect(self.dataFrameChanged)
        self._data_model.dataChanged.connect(self.dataFrameChanged)

        # Create header menu bindings
        self.horizontalHeader().setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.horizontalHeader().customContextMenuRequested.connect(self._header_menu)
        self.verticalHeader().setDefaultSectionSize(25)
        self.setAlternatingRowColors(True)


    def make_cell_context_menu(self, menu, row_ix, col_ix):
        cell_val = self.df.iat[row_ix, col_ix]
        # Quick Filter
        def _quick_filter(s_col):
            return s_col == cell_val

        menu.addAction(self._icon('CommandLink'),
                       "Show =",
                       partial(self._data_model.filterFunction,
                               col_ix=col_ix,
                               function=_quick_filter
                               )
                       )

        # GreaterThan/LessThan filter
        def _cmp_filter(s_col, op):
            return op(s_col, cell_val)

        menu.addAction("Show >",
                       partial(self._data_model.filterFunction,
                               col_ix=col_ix,
                               function=partial(_cmp_filter, op=operator.ge)
                               )
                       )

        menu.addAction("Show <",
                       partial(self._data_model.filterFunction, col_ix=col_ix,
                               function=partial(_cmp_filter, op=operator.le)
                               )
                       )

        menu.addAction(self._icon('DialogResetButton'),
                       "Clear",
                       self._data_model.reset
                       )

        menu.addSeparator()

        # Save to CSV
        def _to_csv():
            from subprocess import Popen
            self.df.to_csv(self.defaultCSVFile)
            Popen(self.defaultCSVFile, shell=True)

        menu.addAction("Open in Excel", _to_excel)
        return menu

    def viewResults_func(self, row_ix):
        self.ViewIndex = row_ix
        self.viewResults.emit()

    def contextMenuEvent(self, event):
        #Implements right-clicking on cell.
        #NOTE: You probably want to overrite make_cell_context_menu, not this
        #function, when subclassing.
        row_ix = self.rowAt(event.y())
        col_ix = self.columnAt(event.x())
        if row_ix < 0 or col_ix < 0:
            return #out of bounds

        menu = QtWidgets.QMenu(self)
        menu = self.make_cell_context_menu(menu, row_ix, col_ix)
        menu.exec_(self.mapToGlobal(event.pos()))

    def _header_menu(self, pos):
        #Create popup menu used for header"""
        menu = QtWidgets.QMenu(self)
        col_ix = self.horizontalHeader().logicalIndexAt(pos)



        if col_ix == -1:
            # Out of bounds
            return

        # Filter Menu Action
        menu.addAction(DynamicFilterMenuAction(self, menu, col_ix))
        menu.addAction(FilterListMenuWidget(self, menu, col_ix))
        menu.addAction(self._icon('DialogResetButton'),
                       "Reset",
                       self._data_model.reset)

        # Sort Ascending/Decending Menu Action

        menu.addAction(self._icon('TitleBarShadeButton'),
                       "Sort Ascending",
                       partial(self._data_model.sort, col_ix=col_ix, order=QtCore.Qt.AscendingOrder))

        menu.addAction(self._icon('TitleBarUnshadeButton'),
                       "Sort Descending",
                       partial(self._data_model.sort, col_ix=col_ix, order=QtCore.Qt.DescendingOrder))
        menu.addSeparator()

        # Hide
        menu.addAction("Hide", partial(self.hideColumn, col_ix))


        # Show (column to left and right)
        for i in (-1, 1):
            if self.isColumnHidden(col_ix+i):
                menu.addAction("Show %s" % self._data_model.headerData(col_ix+i, QtCore.Qt.Horizontal),
                               partial(self.showColumn, col_ix+i))
        menu.exec_(self.mapToGlobal(pos))


    def setDataFrame(self, df):
        self._data_model.setDataFrame(df)

        #self.resizeColumnsToContents()

    def filter(self, col_ix, needle):
        return self._data_model.filter(col_ix, needle)

    def filterIsIn(self, col_ix, include):
        return self._data_model.filterIsIn(col_ix, include)

    @property
    def df(self):
        return self._data_model.df

    @df.setter
    def df(self, dataFrame):
        self._data_model.setDataFrame(dataFrame)


    def keyPressEvent(self, event):
        if event.matches(QtGui.QKeySequence.Copy):
            self.copy()
        else:
            super(QTableViewWidget, self).keyPressEvent(event)

    def copy(self):
        selection = self.selectionModel()
        indexes = selection.selectedIndexes()
        if len(indexes) < 1:
            return
        items = pandas.DataFrame()
        for idx in indexes:
            row = idx.row()
            col = idx.column()
            item = idx.data()
            if item:
                items = items.set_value(row, col, str(item)

        items.to_clipboard(sep='\t', index=False)

    def _icon(self, icon_name):
        """Convinence function to get standard icons from Qt"""
        if not icon_name.startswith('SP_'):
            icon_name = 'SP_' + icon_name
        icon = getattr(QtWidgets.QStyle, icon_name, None)
        if icon is None:
            raise Exception("Unknown icon %s" % icon_name)
        return self.style().standardIcon(icon)






