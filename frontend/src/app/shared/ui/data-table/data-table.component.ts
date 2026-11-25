import {
  ChangeDetectionStrategy,
  Component,
  computed,
  input,
  model,
  output,
  signal,
} from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { IconComponent } from '../icon/icon.component';
import { TableColumn, TableActionClick } from './data-table.models';

@Component({
  selector: 'app-data-table',
  standalone: true,
  imports: [CommonModule, FormsModule, IconComponent],
  templateUrl: './data-table.component.html',
  styleUrl: './data-table.component.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class DataTableComponent<T = any> {
  // Columns & Data inputs
  readonly columns = input<TableColumn<T>[]>([]);
  readonly data = input<T[]>([]);

  // Search configurations
  readonly searchable = input<boolean>(true);
  readonly searchPlaceholder = input<string>('Search by role...');
  readonly searchQuery = model<string>('');

  // Filter configurations
  readonly showFilter = input<boolean>(true);
  readonly filterLabel = input<string>('Access scope');
  readonly filterOptions = input<string[]>(['Department', 'Organization', 'All']);
  readonly selectedFilter = model<string>('Department');

  // Pagination configurations
  readonly showPagination = input<boolean>(true);
  readonly pageSize = input<number>(10);
  readonly currentPage = model<number>(1);
  readonly itemLabel = input<string>('users');
  readonly totalItems = input<number | null>(null);
  readonly totalPagesOverride = input<number | null>(null);

  // Accessibility & custom caption
  readonly caption = input<string>('');

  // Sorting signals
  readonly sortKey = signal<string>('');
  readonly sortDirection = signal<'asc' | 'desc'>('asc');

  // Outputs
  readonly rowClick = output<T>();
  readonly actionClick = output<TableActionClick<T>>();
  readonly filterChange = output<string>();
  readonly pageChange = output<number>();

  /**
   * Filtered dataset based on internal search query and filter selection.
   */
  readonly filteredData = computed(() => {
    let dataset = [...(this.data() || [])];
    const query = this.searchQuery().trim().toLowerCase();

    // 1. Search filter across all visible column keys or row string fields
    if (query) {
      dataset = dataset.filter((row: any) => {
        if (!row) return false;
        return Object.entries(row).some(([key, val]) => {
          if (val === null || val === undefined) return false;
          return String(val).toLowerCase().includes(query);
        });
      });
    }

    // 2. Sorting
    const key = this.sortKey();
    if (key) {
      const dir = this.sortDirection() === 'asc' ? 1 : -1;
      dataset.sort((a: any, b: any) => {
        const valA = a?.[key] ?? '';
        const valB = b?.[key] ?? '';
        if (typeof valA === 'number' && typeof valB === 'number') {
          return (valA - valB) * dir;
        }
        return String(valA).localeCompare(String(valB)) * dir;
      });
    }

    return dataset;
  });

  /**
   * Total count of filtered items (or externally provided totalItems)
   */
  readonly totalCalculated = computed(() => {
    const ext = this.totalItems();
    return ext !== null && ext !== undefined ? ext : this.filteredData().length;
  });

  /**
   * Total number of pages
   */
  readonly totalPages = computed(() => {
    const size = this.pageSize();
    if (size <= 0) return 1;
    return this.totalPagesOverride() ?? Math.max(1, Math.ceil(this.totalCalculated() / size));
  });

  /**
   * Current slice of items for the active page
   */
  readonly paginatedData = computed(() => {
    const all = this.filteredData();
    const size = this.pageSize();
    if (!this.showPagination() || size <= 0) {
      return all;
    }
    const start = (this.currentPage() - 1) * size;
    return all.slice(start, start + size);
  });

  /**
   * Array of page numbers to render in pagination controls
   */
  readonly pageNumbers = computed(() => {
    const count = this.totalPages();
    const current = this.currentPage();
    const pages: number[] = [];

    // For compact pagination, display available page numbers
    const start = Math.max(1, current - 2);
    const end = Math.min(count, start + 4);
    for (let i = start; i <= end; i++) {
      pages.push(i);
    }
    return pages;
  });

  /**
   * Showing count label (e.g. "4" if on single page, or "1 - 10" if paginated)
   */
  readonly showingCountDisplay = computed(() => {
    const total = this.totalCalculated();
    if (total === 0) return '0';
    const size = this.pageSize();
    if (total <= size) {
      return `${total}`;
    }
    const start = (this.currentPage() - 1) * size + 1;
    const end = Math.min(this.currentPage() * size, total);
    return `${start}-${end}`;
  });

  // Search input handler
  onSearchInput(event: Event): void {
    const input = event.target as HTMLInputElement;
    this.searchQuery.set(input.value);
    this.currentPage.set(1);
  }

  // Clear search input
  clearSearch(): void {
    this.searchQuery.set('');
    this.currentPage.set(1);
  }

  // Filter dropdown change handler
  onFilterChange(event: Event): void {
    const select = event.target as HTMLSelectElement;
    this.selectedFilter.set(select.value);
    this.filterChange.emit(select.value);
    this.currentPage.set(1);
  }

  // Column sort toggle
  onSort(key: string): void {
    if (this.sortKey() === key) {
      if (this.sortDirection() === 'asc') {
        this.sortDirection.set('desc');
      } else {
        this.sortKey.set('');
        this.sortDirection.set('asc');
      }
    } else {
      this.sortKey.set(key);
      this.sortDirection.set('asc');
    }
  }

  // Pagination navigation
  goToPage(page: number): void {
    const target = Math.max(1, Math.min(page, this.totalPages()));
    if (target !== this.currentPage()) {
      this.currentPage.set(target);
      this.pageChange.emit(target);
    }
  }

  // Trigger row action button click
  triggerAction(action: string, row: T, index: number): void {
    this.actionClick.emit({ action, row, index });
  }

  // Safely extract cell value
  getCellValue(row: any, col: TableColumn<T>): any {
    if (!row) return '';
    const raw = row[col.key];
    if (col.render) {
      return col.render(raw, row);
    }
    return raw ?? '';
  }

  // Badge status helpers
  isStatusActive(value: any): boolean {
    const str = String(value || '').toLowerCase().trim();
    return str === 'active' || str === 'enabled' || str === 'approved';
  }

  isStatusPending(value: any): boolean {
    const str = String(value || '').toLowerCase().trim();
    return str === 'pending' || str === 'in progress' || str === 'on leave';
  }

  isStatusInactive(value: any): boolean {
    const str = String(value || '').toLowerCase().trim();
    return str === 'inactive' || str === 'disabled' || str === 'terminated' || str === 'rejected';
  }

  // Row tracker function
  trackByFn(index: number, item: any): any {
    return item?.id ?? item?.role ?? index;
  }
}
