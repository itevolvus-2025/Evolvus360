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
import { Router, RouterLink } from '@angular/router';
import { IconComponent } from '../../../../shared/ui/icon/icon.component';
import { NotificationService } from '../../../../core/services/notification.service';
import { UserService, UserRow } from '../../data-access/user.service';

@Component({
  selector: 'app-user-list',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterLink, IconComponent],
  templateUrl: './user-list.component.html',
  styleUrl: './user-list.component.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class UserListComponent implements OnInit {
  private readonly userService = inject(UserService);
  private readonly router = inject(Router);
  private readonly notification = inject(NotificationService);
  readonly userServiceRef = this.userService;

  ngOnInit(): void {
    this.userService.loadUsers();
  }

  // KPI Metrics signals
  readonly activeCount = this.userService.activeUsersCount;
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

  // Delete State
  readonly userToDeactivate = signal<UserRow | null>(null);
  readonly isDeactivating = signal(false);
  readonly retryingUserIds = signal<Set<string>>(new Set());

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

  openDeactivateModal(user: UserRow): void {
    this.userToDeactivate.set(user);
  }

  closeDeactivateModal(): void {
    this.userToDeactivate.set(null);
  }

  confirmDeactivate(): void {
    const user = this.userToDeactivate();
    if (user) {
      this.isDeactivating.set(true);
      this.userService.deactivateEmployee(
        user.id,
        () => {
          this.isDeactivating.set(false);
          this.notification.show(`User "${user.name}" has been deactivated successfully.`, 'success');
          this.userToDeactivate.set(null);
        },
        (errMsg) => {
          this.isDeactivating.set(false);
          this.notification.show(errMsg, 'error');
        }
      );
    }
  }

  retryInvitation(user: UserRow): void {
    this.retryingUserIds.update((ids) => new Set(ids).add(String(user.id)));
    this.userService.retryInvitation(user.id, (success, message) => {
      this.retryingUserIds.update((ids) => {
        const next = new Set(ids);
        next.delete(String(user.id));
        return next;
      });
      this.notification.show(message, success ? 'success' : 'error');
    });
  }

  sendInvitation(user: UserRow): void {
    const key = String(user.id);
    this.retryingUserIds.update((ids) => new Set(ids).add(key));
    this.userService.sendInvitation(user.id, (success, message) => {
      this.retryingUserIds.update((ids) => {
        const next = new Set(ids);
        next.delete(key);
        return next;
      });
      this.notification.show(message, success ? 'success' : 'error');
    });
  }

  canRetryInvitation(user: UserRow): boolean {
    const invitationCanBeSent = user.profile === 'Pending' && user.status === 'Pending';
    return invitationCanBeSent && (
      user.emailDispatchStatus === 'FAILED' ||
      this.userService.failedInvitationIds().has(String(user.id))
    );
  }

  userIdKey(id: string | number): string {
    return String(id);
  }
}
