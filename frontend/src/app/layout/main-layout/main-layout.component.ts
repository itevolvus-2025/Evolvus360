import {
  ChangeDetectionStrategy,
  Component,
  OnInit,
  computed,
  inject,
  signal,
} from '@angular/core';
import {
  Router,
  RouterLink,
  RouterLinkActive,
  RouterOutlet,
  NavigationEnd,
} from '@angular/router';
import { filter } from 'rxjs/operators';
import { AuthService } from '../../core/services/auth.service';
import { ThemeService } from '../../core/services/theme.service';
import { NotificationDropdownComponent } from '../../shared/components/notification-dropdown/notification-dropdown.component';
import { ToastContainerComponent } from '../../shared/components/toast-container/toast-container.component';
import { IconComponent } from '../../shared/ui/icon/icon.component';

export type SubpageActionType =
  | 'none'
  | 'user-create'
  | 'role-create'
  | 'user-add'
  | 'user-edit'
  | 'role-add'
  | 'role-edit';

interface WorkspaceNavItem {
  label: string;
  path: string;
  icon: string;
  permission: string;
}

interface PageState {
  isSubpage: boolean;
  parentLabel?: string;
  parentPath?: string;
  currentLabel?: string;
  title?: string;
  badge?: string;
  subtitle: string;
  actionType: SubpageActionType;
  actionLabel?: string;
  actionRoute?: string;
}

@Component({
  selector: 'app-main-layout',
  standalone: true,
  imports: [
    RouterOutlet,
    RouterLink,
    RouterLinkActive,
    ToastContainerComponent,
    NotificationDropdownComponent,
    IconComponent,
  ],
  templateUrl: './main-layout.component.html',
  styleUrl: './main-layout.component.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class MainLayoutComponent implements OnInit {
  readonly auth = inject(AuthService);
  readonly theme = inject(ThemeService);
  private readonly router = inject(Router);

  /** Whether the sidebar is collapsed */
  readonly collapsed = signal(false);

  /** Active child component mounted in <router-outlet> for action delegation */
  private readonly activeChildComponent = signal<any>(null);

  /** User profile display (matching uploaded design with Asha Rao / Super Admin) */
  readonly userName = computed(() => this.auth.user()?.name || 'Asha Rao');
  readonly userRole = computed(() => this.auth.user()?.role || 'Super Admin');
  readonly userInitials = computed(() => {
    const name = this.userName().trim();
    if (!name) return 'AR';
    const parts = name.split(/\s+/);
    if (parts.length >= 2) {
      return (parts[0][0] + parts[1][0]).toUpperCase();
    }
    return name.substring(0, 2).toUpperCase();
  });

  /** Master list of navigation items mapped to role permissions */
  readonly allNavItems: WorkspaceNavItem[] = [
    { label: 'Dashboard', path: '/dashboard', icon: 'grid-dashboard', permission: 'Dashboard' },
    {
      label: 'Role Management',
      path: '/administration',
      icon: 'role-management',
      permission: 'Role Management',
    },
    { label: 'Users Management', path: '/users', icon: 'users', permission: 'User Management' },
    { label: 'Approval Hub', path: '/approval-hub', icon: 'approval-hub', permission: 'Approval' },
    { label: 'Projects', path: '/projects', icon: 'folder', permission: 'Project' },
    { label: 'Leave Request', path: '/leave/request', icon: 'calendar-plus', permission: 'Leave Request' },
    { label: 'Leave Management', path: '/leave', icon: 'calendar', permission: 'Leave Management' },
  ];

  /** Reactive navigation items filtered dynamically based on the logged-in user's permissions */
  readonly workspaceNav = computed(() =>
    this.allNavItems.filter((item) => this.auth.hasPermission(item.permission))
  );

  readonly currentUrl = signal(this.router.url);

  constructor() {
    this.router.events
      .pipe(filter((event) => event instanceof NavigationEnd))
      .subscribe((event) => {
        this.currentUrl.set((event as NavigationEnd).urlAfterRedirects);
        this.redirectIfNoAccess();
      });
  }

  ngOnInit(): void {
    this.redirectIfNoAccess();
  }

  private redirectIfNoAccess(): void {
    const current = (this.router.url || '').split('?')[0].split('#')[0];
    if (current === '/dashboard' || current === '' || current === '/') {
      const allowed = this.workspaceNav();
      const hasDashboard = allowed.some((item) => item.path === '/dashboard');
      if (!hasDashboard && allowed.length > 0) {
        void this.router.navigateByUrl(allowed[0].path);
      }
    }
  }

  readonly pageState = computed<PageState>(() => {
    const url = this.currentUrl().split('?')[0].split('#')[0];

    // 1. Subpage: Add User
    if (url === '/users/new' || url === '/employees/new') {
      return {
        isSubpage: true,
        parentLabel: 'User Management',
        parentPath: '/users',
        currentLabel: 'Add user',
        subtitle: 'Manage enterprise access privileges and identity profiles.',
        actionType: 'user-add',
      };
    }

    // 2. Subpage: Edit User
    if (
      url.startsWith('/users/edit/') ||
      url.match(/^\/users\/\d+\/edit$/) ||
      url.startsWith('/employees/edit/') ||
      url.match(/^\/employees\/\d+\/edit$/)
    ) {
      return {
        isSubpage: true,
        parentLabel: 'User Management',
        parentPath: '/users',
        currentLabel: 'Edit user',
        subtitle: 'Manage enterprise access privileges and identity profiles.',
        actionType: 'user-edit',
      };
    }

    // 3. Subpage: Add Role
    if (url === '/administration/roles/new') {
      return {
        isSubpage: true,
        parentLabel: 'Role Management',
        parentPath: '/administration',
        currentLabel: 'Add role',
        subtitle: 'Create and maintain roles',
        actionType: 'role-add',
      };
    }

    // 4. Subpage: Edit Role
    if (
      url.startsWith('/administration/roles/edit/') ||
      url.match(/^\/administration\/roles\/\d+\/edit$/)
    ) {
      return {
        isSubpage: true,
        parentLabel: 'Role Management',
        parentPath: '/administration',
        currentLabel: 'Edit role',
        subtitle: 'Create and maintain roles',
        actionType: 'role-edit',
      };
    }

    // 5. Main Page: User Management
    if (url === '/users' || url === '/employees') {
      return {
        isSubpage: false,
        title: 'Users Management',
        badge: '3 Total',
        subtitle: 'Manage enterprise access privileges and identity profiles.',
        actionType: 'user-create',
        actionLabel: 'Create User',
        actionRoute: '/users/new',
      };
    }

    // 6. Main Page: Role Management
    if (url === '/administration' || url === '/administration/roles') {
      return {
        isSubpage: false,
        title: 'Role Management',
        badge: '3 Total',
        subtitle: 'Create and maintain roles',
        actionType: 'role-create',
        actionLabel: 'Add Role',
        actionRoute: '/administration/roles/new',
      };
    }

    // Dashboard
    if (url === '/dashboard') {
      return {
        isSubpage: false,
        title: 'Dashboard',
        badge: '',
        subtitle: 'Overview of enterprise workforce operations and analytics.',
        actionType: 'none',
      };
    }

    // Approval Hub 
    if (url === '/approval-hub' || url.startsWith('/approval-hub')) {
      return {
        isSubpage: false,
        title: 'Approval Hub',
        badge: '3 Total',
        subtitle:
          'Review and authorize company-wide requests, employee onboarding credentials, leaves and role escalations.',
        actionType: 'none',
      };
    }

    // Projects
    if (url === '/projects' || url.startsWith('/projects/')) {
      return {
        isSubpage: false,
        title: 'Projects',
        badge: '4 Total',
        subtitle: 'Manage organizational projects, delivery milestones, and team assignments.',
        actionType: 'none',
      };
    }

    // Leave Request
    if (url === '/leave/request') {
      return {
        isSubpage: false,
        title: 'Leave Request',
        badge: '',
        subtitle: 'Apply for time off and track status of personal leave applications.',
        actionType: 'none',
      };
    }

    // Leave Management
    if (url === '/leave') {
      return {
        isSubpage: false,
        title: 'Leave Management',
        badge: '',
        subtitle: 'Track balances, review leave requests, and manage approval workflows.',
        actionType: 'none',
      };
    }

    // Fallback for administration child paths
    if (url.startsWith('/administration/')) {
      if (url.includes('new') || url.includes('add')) {
        return {
          isSubpage: true,
          parentLabel: 'Role Management',
          parentPath: '/administration',
          currentLabel: 'Add role',
          subtitle: 'Create and maintain roles',
          actionType: 'role-add',
        };
      }
      if (url.includes('edit')) {
        return {
          isSubpage: true,
          parentLabel: 'Role Management',
          parentPath: '/administration',
          currentLabel: 'Edit role',
          subtitle: 'Create and maintain roles',
          actionType: 'role-edit',
        };
      }
      return {
        isSubpage: false,
        title: 'Role Management',
        badge: '3 Total',
        subtitle: 'Create and maintain roles',
        actionType: 'role-create',
        actionLabel: 'Add Role',
        actionRoute: '/administration/roles/new',
      };
    }

    // Default Fallback
    return {
      isSubpage: false,
      title: 'Users Management',
      badge: '3 Total',
      subtitle: 'Manage enterprise access privileges and identity profiles.',
      actionType: 'none',
    };
  });

  readonly isSubpage = computed(() => this.pageState().isSubpage);
  readonly breadcrumbParentLabel = computed(() => this.pageState().parentLabel ?? '');
  readonly breadcrumbParentPath = computed(() => this.pageState().parentPath ?? '');
  readonly breadcrumbCurrentLabel = computed(() => this.pageState().currentLabel ?? '');
  readonly activePageTitle = computed(() => this.pageState().title ?? '');
  readonly activePageBadge = computed(() => this.pageState().badge ?? '');
  readonly activePageSubtitle = computed(() => this.pageState().subtitle ?? '');
  readonly actionType = computed(() => this.pageState().actionType);
  readonly actionLabel = computed(() => this.pageState().actionLabel ?? '');
  readonly actionRoute = computed(() => this.pageState().actionRoute ?? '');

  toggleSidebar(): void {
    this.collapsed.update((value) => !value);
  }

  onComponentActivate(component: any): void {
    this.activeChildComponent.set(component);
  }

  onComponentDeactivate(): void {
    this.activeChildComponent.set(null);
  }

  triggerSave(): void {
    const comp = this.activeChildComponent();
    if (!comp) return;
    if (typeof comp.saveUser === 'function') {
      comp.saveUser();
    } else if (typeof comp.saveRole === 'function') {
      comp.saveRole();
    }
  }

  triggerDelete(): void {
    const comp = this.activeChildComponent();
    if (!comp) return;
    if (typeof comp.openDeleteConfirm === 'function') {
      comp.openDeleteConfirm();
    }
  }
}
