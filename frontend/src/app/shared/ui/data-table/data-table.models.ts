export type ColumnType = 'text' | 'badge' | 'action' | 'date' | 'custom';

export interface TableColumn<T = any> {
  /** Property key on row object (e.g. 'role', 'purpose', 'status') */
  key: string;

  /** Column header title displayed in the thead (e.g. 'ROLE', 'STATUS') */
  header: string;

  /** Optional column width (e.g. '200px', '25%') */
  width?: string;

  /** Alignment of column text (defaults to 'left') */
  align?: 'left' | 'center' | 'right';

  /** Whether the column can be sorted */
  sortable?: boolean;

  /** Rendering type: 'text', 'badge', 'action', or 'custom' */
  type?: ColumnType;

  /** Custom badge variant evaluator function */
  badgeVariant?: (value: any, row: T) => 'success' | 'warning' | 'danger' | 'info' | 'default';

  /** Icon name for action column (defaults to 'edit') */
  actionIcon?: string;

  /** Icon color for action column (defaults to '#2563EB') */
  actionColor?: string;

  /** Tooltip for action column button */
  actionTooltip?: string;

  /** Custom text rendering/formatting function */
  render?: (value: any, row: T) => string;

  /** Optional custom CSS class for td cells */
  cssClass?: string;
}

export interface TableActionClick<T = any> {
  action: string;
  row: T;
  index: number;
}
