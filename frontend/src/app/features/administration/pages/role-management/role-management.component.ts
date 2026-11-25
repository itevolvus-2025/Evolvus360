import {
  ChangeDetectionStrategy,
  Component,
  OnInit,
  OnDestroy,
  computed,
  inject,
  signal,
} from '@angular/core';
import { CommonModule } from '@angular/common';
import { Router, RouterLink } from '@angular/router';
import { IconComponent } from '../../../../shared/ui/icon/icon.component';
import { DropdownOption } from '../../../../shared/ui/dropdown';
import { NotificationService } from '../../../../core/services/notification.service';
import { RoleService, RoleRow } from '../../data-access/role.service';

@Component({
  selector: 'app-role-management',
  standalone: true,
  imports: [CommonModule, RouterLink, IconComponent],
  templateUrl: './role-management.component.html',
  styleUrl: './role-management.component.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class RoleManagementComponent implements OnInit, OnDestroy {
  private readonly router = inject(Router);
  private readonly roleService = inject(RoleService);
  private readonly notification = inject(NotificationService);

  readonly isLoading = this.roleService.isLoading;
  readonly loadError = computed(() => this.roleService.loadError());

  /** Access scope dropdown filter */
  readonly selectedScope = signal<string>('Department');
  readonly scopeOptions: DropdownOption[] = [
    { label: 'Department', value: 'Department' },
    { label: 'Organization', value: 'Organization' },
    { label: 'All', value: 'All' },
  ];

  /** Search query signal */
  readonly searchQuery = signal('');

  /** Active pagination state */
  readonly currentPage = signal(1);
  readonly pageSize = 10;

  /** Live dataset directly populated by backend API */
  readonly roles = this.roleService.roles;
  readonly totalRoleCount = this.roleService.totalRoleCount;
  readonly totalRolePages = this.roleService.totalRolePages;

  /** Array of page numbers for pagination buttons */
  readonly pages = computed(() => {
    const total = this.totalRolePages();
    return Array.from({ length: total }, (_, i) => i + 1);
  });

  private searchDebounceTimer: any = null;

  ngOnInit(): void {
    this.fetchRoles();
  }

  ngOnDestroy(): void {
    if (this.searchDebounceTimer) {
      clearTimeout(this.searchDebounceTimer);
    }
  }

  /**
   * Dispatches backend API call with current page, pageSize, and search query
   */
  fetchRoles(): void {
    this.roleService.loadRoles(
      this.currentPage(),
      this.pageSize,
      this.searchQuery()
    );
  }

  goToPage(page: number): void {
    if (page < 1 || page > this.totalRolePages()) return;
    this.currentPage.set(page);
    this.fetchRoles();
  }

  onSearchInput(event: Event): void {
    const value = (event.target as HTMLInputElement).value;
    this.searchQuery.set(value);
    this.currentPage.set(1);

    if (this.searchDebounceTimer) {
      clearTimeout(this.searchDebounceTimer);
    }
    this.searchDebounceTimer = setTimeout(() => {
      this.fetchRoles();
    }, 300);
  }

  clearSearch(): void {
    this.searchQuery.set('');
    this.currentPage.set(1);
    this.fetchRoles();
  }

  onScopeChange(scope: string): void {
    this.selectedScope.set(scope);
    this.currentPage.set(1);
    this.fetchRoles();
  }

  editRole(role: RoleRow): void {
    void this.router.navigate(['/administration/roles/edit', role.id]);
  }
}
