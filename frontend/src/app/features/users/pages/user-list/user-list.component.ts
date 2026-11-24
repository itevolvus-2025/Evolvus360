import {
  ChangeDetectionStrategy,
  Component,
  OnInit,
  computed,
  inject,
  signal,
} from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { RouterLink } from '@angular/router';
import { IconComponent } from '../../../../shared/ui/icon/icon.component';
import { DropdownComponent } from '../../../../shared/ui/dropdown';
import { UserService } from '../../data-access/user.service';

@Component({
  selector: 'app-user-list',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterLink, IconComponent, DropdownComponent],
  templateUrl: './user-list.component.html',
  styleUrl: './user-list.component.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class UserListComponent implements OnInit {
  private readonly userService = inject(UserService);
  readonly userLoadError = this.userService.loadError;

  readonly roleFilterOptions = [
    { label: 'All Roles', value: 'All' },
    { label: 'Super Admin', value: 'Super Admin' },
    { label: 'HR Manager', value: 'HR Manager' },
    { label: 'Employee', value: 'Employee' },
  ];

  ngOnInit(): void {
    this.userService.loadUsers();
  }

  // KPI Metrics signals
  readonly activeCount = this.userService.activeUsersCount;
  readonly totalUserCount = this.userService.totalUsersCount;
  readonly awaitingCount = this.userService.awaitingActivationCount;
  readonly pendingCount = this.userService.requestsPendingCount;
  readonly submittedCount = this.userService.profilesSubmittedCount;

  // Search and Filter State
  readonly searchQuery = signal('');
  readonly filterRole = signal('All');
  readonly isFilterOpen = signal(false);

  // Pagination State
  readonly currentPage = signal(1);
  readonly pageSize = signal(10);

  /** Filtered users based on search input and role filter */
  readonly filteredUsers = computed(() => {
    let list = this.userService.users();
    const query = this.searchQuery().trim().toLowerCase();
    const role = this.filterRole();

    if (role !== 'All') {
      list = list.filter((u) => u.role.toLowerCase() === role.toLowerCase());
    }

    if (query) {
      list = list.filter(
        (u) =>
          u.name.toLowerCase().includes(query) ||
          u.code.toLowerCase().includes(query) ||
          u.role.toLowerCase().includes(query) ||
          u.email.toLowerCase().includes(query)
      );
    }

    return list;
  });

  readonly totalUsers = computed(() => this.filteredUsers().length);

  readonly totalPages = computed(() => {
    const size = this.pageSize();
    return Math.max(1, Math.ceil(this.totalUsers() / size));
  });

  readonly paginatedUsers = computed(() => {
    const start = (this.currentPage() - 1) * this.pageSize();
    return this.filteredUsers().slice(start, start + this.pageSize());
  });

  readonly pageNumbers = computed(() => {
    const count = this.totalPages();
    const pages: number[] = [];
    for (let i = 1; i <= count; i++) {
      pages.push(i);
    }
    return pages;
  });

  getInitials(name: string): string {
    const trimmed = (name || '').trim();
    if (!trimmed) return 'U';
    const parts = trimmed.split(/\s+/);
    if (parts.length >= 2) {
      return (parts[0][0] + parts[1][0]).toUpperCase();
    }
    return trimmed.substring(0, 2).toUpperCase();
  }

  onSearchInput(event: Event): void {
    const input = event.target as HTMLInputElement;
    this.searchQuery.set(input.value);
    this.currentPage.set(1);
  }

  clearSearch(): void {
    this.searchQuery.set('');
    this.currentPage.set(1);
  }

  toggleFilterDropdown(): void {
    this.isFilterOpen.update((v) => !v);
  }

  setFilter(role: string): void {
    this.filterRole.set(role);
    this.isFilterOpen.set(false);
    this.currentPage.set(1);
  }

  goToPage(page: number): void {
    const target = Math.max(1, Math.min(page, this.totalPages()));
    this.currentPage.set(target);
  }

}
