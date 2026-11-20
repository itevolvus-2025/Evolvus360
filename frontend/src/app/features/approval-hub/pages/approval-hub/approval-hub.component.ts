import {
  ChangeDetectionStrategy,
  Component,
  computed,
  inject,
  signal,
} from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { IconComponent } from '../../../../shared/ui/icon/icon.component';
import {
  ApprovalHubService,
  ApprovalItem,
} from '../../data-access/approval-hub.service';

export type FilterOption =
  | 'Pending Only'
  | 'All Requests'
  | 'Employee Onboarding'
  | 'Leaves & Time-off'
  | 'Authorized'
  | 'Rejected';

@Component({
  selector: 'app-approval-hub',
  standalone: true,
  imports: [CommonModule, FormsModule, IconComponent],
  templateUrl: './approval-hub.component.html',
  styleUrl: './approval-hub.component.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class ApprovalHubComponent {
  private readonly approvalService = inject(ApprovalHubService);

  // KPI Metrics signals
  readonly totalPending = this.approvalService.totalPending;
  readonly onboardingCount = this.approvalService.employeeOnboardingCount;
  readonly leavesCount = this.approvalService.leavesCount;
  readonly authorizedCount = this.approvalService.authorizedCount;
  readonly totalCount = this.approvalService.totalCount;

  // Search & Filter State
  readonly searchQuery = signal('');
  readonly selectedFilter = signal<FilterOption>('Pending Only');
  readonly isFilterOpen = signal(false);

  /** Filtered list based on status filter and search query */
  readonly filteredItems = computed<ApprovalItem[]>(() => {
    let list = this.approvalService.items();
    const filter = this.selectedFilter();
    const query = this.searchQuery().trim().toLowerCase();

    // 1. Status Filter
    if (filter === 'Pending Only') {
      list = list.filter((item) => item.status === 'Pending');
    } else if (filter === 'Authorized') {
      list = list.filter((item) => item.status === 'Authorized');
    } else if (filter === 'Rejected') {
      list = list.filter((item) => item.status === 'Rejected');
    } else if (filter === 'Employee Onboarding') {
      list = list.filter((item) => item.type === 'EMPLOYEE ONBOARDING');
    } else if (filter === 'Leaves & Time-off') {
      list = list.filter((item) => item.type === 'LEAVES & TIME-OFF');
    }

    // 2. Search Query
    if (query) {
      list = list.filter(
        (item) =>
          item.title.toLowerCase().includes(query) ||
          item.description.toLowerCase().includes(query) ||
          item.department.toLowerCase().includes(query) ||
          item.submittedBy.toLowerCase().includes(query) ||
          item.assignedRole.toLowerCase().includes(query) ||
          item.admin.toLowerCase().includes(query)
      );
    }

    return list;
  });

  toggleFilterDropdown(): void {
    this.isFilterOpen.update((open) => !open);
  }

  setFilter(option: FilterOption): void {
    this.selectedFilter.set(option);
    this.isFilterOpen.set(false);
  }

  authorize(id: string | number): void {
    this.approvalService.authorize(id);
  }

  reject(id: string | number): void {
    this.approvalService.reject(id);
  }
}
