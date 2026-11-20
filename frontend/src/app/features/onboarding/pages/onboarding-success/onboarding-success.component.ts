import { ChangeDetectionStrategy, Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterLink } from '@angular/router';
import { IconComponent } from '../../../../shared/ui/icon/icon.component';

@Component({
  selector: 'app-onboarding-success',
  standalone: true,
  imports: [CommonModule, RouterLink, IconComponent],
  templateUrl: './onboarding-success.component.html',
  styleUrl: './onboarding-success.component.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class OnboardingSuccessComponent {}
