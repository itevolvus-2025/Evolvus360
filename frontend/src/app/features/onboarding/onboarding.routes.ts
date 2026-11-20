import { Routes } from '@angular/router';

export const ONBOARDING_ROUTES: Routes = [
  {
    path: '',
    loadComponent: () =>
      import('./pages/onboarding/onboarding.component').then(
        (m) => m.OnboardingComponent
      ),
  },
  {
    path: 'success',
    loadComponent: () =>
      import('./pages/onboarding-success/onboarding-success.component').then(
        (m) => m.OnboardingSuccessComponent
      ),
  },
  {
    path: ':token',
    loadComponent: () =>
      import('./pages/onboarding/onboarding.component').then(
        (m) => m.OnboardingComponent
      ),
  },
];
