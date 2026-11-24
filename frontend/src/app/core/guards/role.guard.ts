import { inject } from '@angular/core';
import { CanActivateFn, Router } from '@angular/router';
import { AuthService } from '../services/auth.service';

export const roleGuard: CanActivateFn = (route) => {
  const auth = inject(AuthService);
  const router = inject(Router);
  if (!auth.isAuthenticated()) {
    return router.createUrlTree(['/auth/login']);
  }

  const roles = route.data?.['roles'] as string[] | undefined;
  const permissions = route.data?.['permissions'] as string[] | undefined;
  const user = auth.user();

  if (roles?.length && user && !roles.includes(user.role)) {
    return router.createUrlTree(['/access-denied']);
  }
  if (permissions?.length && !auth.hasAnyPermission(permissions)) {
    return router.createUrlTree(['/access-denied']);
  }
  if (!roles?.length && !permissions?.length) {
    return true;
  }

  return true;
};
