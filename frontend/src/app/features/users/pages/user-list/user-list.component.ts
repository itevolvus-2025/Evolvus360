import {
  ChangeDetectionStrategy,
  Component,
  OnDestroy,
  OnInit,
  computed,
  inject,
  signal,
} from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { RouterLink } from '@angular/router';
import { IconComponent } from '../../../../shared/ui/icon/icon.component';
import { DropdownComponent, DropdownOption } from '../../../../shared/ui/dropdown';
import { UserService, UserRow } from '../../data-access/user.service';
import { RoleService } from '../../../administration/data-access/role.service';
import { NotificationService } from '../../../../core/services/notification.service';

@Component({
  selector: 'app-user-list',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterLink, IconComponent, DropdownComponent],
  templateUrl: './user-list.component.html',
  styleUrl: './user-list.component.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class UserListComponent implements OnInit, OnDestroy {
  private readonly userService = inject(UserService);
  private readonly roleService = inject(RoleService);
  private readonly notification = inject(NotificationService);
  readonly userLoadError = this.userService.loadError;

  private searchDebounceTimer: any = null;

  /**
   * Dynamically build role filter dropdown options from both Role API (/api/v1/roles)
   * and Master Data Role API (/api/v1/master-data/roles).
   */
  readonly roleFilterOptions = computed<DropdownOption[]>(() => {
    const options: DropdownOption[] = [{ label: 'All Roles', value: 'All' }];
    const seen = new Set<string>();

    // Roles from live RoleService
    for (const r of this.roleService.roles()) {
      const name = (r.role || '').trim();
      if (name && !seen.has(name.toLowerCase())) {
        seen.add(name.toLowerCase());
        options.push({ label: name, value: name });
      }
    }

    // Roles from UserService master data
    for (const r of this.userService.roles()) {
      const name = (r.name || '').trim();
      if (name && !seen.has(name.toLowerCase())) {
        seen.add(name.toLowerCase());
        options.push({ label: name, value: name });
      }
    }

    return options;
  });

  ngOnInit(): void {
    // Load live roles from Role API and Master Data API
    this.roleService.loadRoles(1, 100);
    this.userService.loadMasterData();
    this.loadUsersData();
  }

  ngOnDestroy(): void {
    if (this.searchDebounceTimer) {
      clearTimeout(this.searchDebounceTimer);
    }
  }

  // KPI Metrics signals
  readonly activeCount = this.userService.activeUsersCount;
  readonly totalUserCount = this.userService.totalUsersCount;
  readonly awaitingCount = this.userService.awaitingActivationCount;
  readonly pendingCount = this.userService.requestsPendingCount;
  readonly submittedCount = this.userService.profilesSubmittedCount;

  formatPersonName(value: string): string {
    return this.userService.formatPersonName(value);
  }

  // Search and Filter State
  readonly searchQuery = signal('');
  readonly filterRole = signal('All');
  readonly isFilterOpen = signal(false);

  // Pagination State
  readonly currentPage = signal(1);
  readonly pageSize = signal(10);

  private isUuid(val: string): boolean {
    return /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(val);
  }

  /**
   * Resolves the selected role's UUID to send to backend API
   */
  private getSelectedRoleId(): string | undefined {
    const selected = this.filterRole();
    if (!selected || selected === 'All') {
      return undefined;
    }

    // Check master data roles
    const masterRole = this.userService.roles().find(
      (r) => r.name.toLowerCase() === selected.toLowerCase() || String(r.id) === selected
    );
    if (masterRole && this.isUuid(String(masterRole.id))) {
      return String(masterRole.id);
    }

    // Check administration role service
    const adminRole = this.roleService.roles().find(
      (r) => r.role.toLowerCase() === selected.toLowerCase() || String(r.id) === selected
    );
    if (adminRole && this.isUuid(String(adminRole.id))) {
      return String(adminRole.id);
    }

    return undefined;
  }

  /**
   * Fetches users from the backend API applying current pagination, role, and search query.
   */
  private loadUsersData(): void {
    const roleId = this.getSelectedRoleId();
    this.userService.loadUsers(
      this.currentPage(),
      this.pageSize(),
      roleId,
      this.searchQuery()
    );
  }

  /** Filtered users based on search input and role filter (provides instantaneous client filtering) */
  readonly filteredUsers = computed(() => {
    let list = this.userService.users();
    const query = this.searchQuery().trim().toLowerCase();
    const role = this.filterRole();
    const roleId = this.getSelectedRoleId();

    if (role !== 'All') {
      list = list.filter((u) => {
        const uRole = (u.role || '').toLowerCase();
        const targetRole = role.toLowerCase();
        return uRole === targetRole || (roleId && u.roleId === roleId);
      });
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

  readonly totalUsers = this.userService.totalUsersCount;

  readonly totalPages = computed(() => {
    return this.userService.totalUserPages();
  });

  readonly paginatedUsers = computed(() => {
    return this.filteredUsers();
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
    if (this.searchDebounceTimer) {
      clearTimeout(this.searchDebounceTimer);
    }
    this.searchDebounceTimer = setTimeout(() => {
      this.currentPage.set(1);
      this.loadUsersData();
    }, 300);
  }

  clearSearch(): void {
    this.searchQuery.set('');
    if (this.searchDebounceTimer) {
      clearTimeout(this.searchDebounceTimer);
    }
    this.currentPage.set(1);
    this.loadUsersData();
  }

  toggleFilterDropdown(): void {
    this.isFilterOpen.update((v) => !v);
  }

  setFilter(role: string): void {
    this.filterRole.set(role);
    this.isFilterOpen.set(false);
    this.currentPage.set(1);
    this.loadUsersData();
  }

  goToPage(page: number): void {
    const maxPage = Math.max(1, this.totalPages());
    const target = Math.max(1, Math.min(page, maxPage));
    this.currentPage.set(target);
    this.loadUsersData();
  }

  isRejected(user: UserRow): boolean {
    return user.profile === 'Rejected';
  }

  canSendInvitation(user: UserRow): boolean {
    return user.profile === 'Pending' || user.profile === 'Rejected';
  }

  sendInvitation(user: UserRow): void {
    this.userService.sendInvitation(user.id, (success, message) => {
      this.notification.show(message, success ? 'success' : 'error');
    });
  }
}
