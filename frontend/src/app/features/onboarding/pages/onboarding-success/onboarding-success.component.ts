import { ChangeDetectionStrategy, Component } from '@angular/core';

@Component({
  selector: 'app-onboarding-success',
  standalone: true,
  imports: [],
  templateUrl: './onboarding-success.component.html',
  styleUrl: './onboarding-success.component.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class OnboardingSuccessComponent {}
