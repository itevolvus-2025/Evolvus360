import {
  ChangeDetectionStrategy,
  Component,
  OnInit,
  computed,
  inject,
  signal,
} from '@angular/core';
import { CommonModule } from '@angular/common';
import { Router } from '@angular/router';
import { DataTableComponent, TableColumn, TableActionClick } from '../../../../shared/ui/data-table';
import { NotificationService } from '../../../../core/services/notification.service';
import { RoleService, RoleRow } from '../../data-access/role.service';

@Component({
  selector: 'app-role-management',
  standalone: true,
  imports: [CommonModule, DataTableComponent],
  templateUrl: './role-management.component.html',
  styleUrl: './role-management.component.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class RoleManagementComponent implements OnInit {
  private readonly router = inject(Router);
  private readonly roleService = inject(RoleService);
  private readonly notification = inject(NotificationService);

  ngOnInit(): void {
    this.roleService.loadRoles();
  }

  /** Access scope dropdown filter */
  readonly selectedScope = signal<string>('Department');
  readonly scopeOptions = ['Department', 'Organization', 'All'];

  /** Columns configuration for common table matching user's design */
  readonly columns: TableColumn<RoleRow>[] = [
    { key: 'role', header: 'ROLE', sortable: true, width: '22%' },
    { key: 'purpose', header: 'PURPOSE', sortable: true, width: '40%' },
    { key: 'status', header: 'STATUS', type: 'badge', sortable: true, width: '20%' },
    {
      key: 'action',
      header: 'ACTION',
      type: 'action',
      actionIcon: 'edit',
      actionColor: '#2563EB',
      actionTooltip: 'Edit Role',
      width: '18%',
      align: 'left',
    },
  ];

  /** Live dataset from RoleService */
  readonly roles = this.roleService.roles;

  /** Filtered roles (ensuring roles always display for user browsing) */
  readonly filteredRoles = computed(() => {
    const list = this.roles();
    const scope = (this.selectedScope() || '').trim().toLowerCase();

    if (!scope || scope === 'all' || scope === 'department') {
      return list;
    }

    const filtered = list.filter((r) => {
      const rScope = (r.scope || 'all').toLowerCase();
      return rScope === scope || rScope === 'all';
    });

    return filtered.length > 0 ? filtered : list;
  });

  /** Delete confirmation state */
  readonly roleToDelete = signal<RoleRow | null>(null);

  /** Handle action button click from common data-table */
  handleAction(event: TableActionClick<RoleRow>): void {
    if (event.action === 'edit' && event.row) {
      // Navigate to dedicated Edit Role page
      void this.router.navigate(['/administration/roles/edit', event.row.id]);
    } else if (event.action === 'delete' && event.row) {
      this.roleToDelete.set(event.row);
    }
  }

  /** Delete Role confirmation methods */
  closeDeleteModal(): void {
    this.roleToDelete.set(null);
  }

  confirmDelete(): void {
    const role = this.roleToDelete();
    if (role) {
      this.roleService.deleteRole(role.id);
      this.notification.show(`Role "${role.role}" deleted successfully.`, 'info');
      this.roleToDelete.set(null);
    }
  }
}
