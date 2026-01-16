"""
==============================================================================
TRAIN ML MODELS - Django Management Command
==============================================================================
Train or retrain the ShopCredit ML models.

Usage:
    python manage.py train_models              # Train all models
    python manage.py train_models --risk       # Train only risk model
    python manage.py train_models --credit     # Train only credit model
    python manage.py train_models --segment    # Train only segment model
    python manage.py train_models --synthetic  # Use synthetic data for training

Models:
    1. Risk Prediction (Random Forest)
       - Predicts probability of customer defaulting
       - Features: payment history, credit utilization, etc.
    
    2. Credit Limit (Linear Regression)
       - Suggests appropriate credit limit
       - Based on monthly revenue and payment behavior
    
    3. Shop Segment (K-Means Clustering)
       - Groups customers into segments
       - Low Activity, Regular, High Value, At Risk

Author: ShopCredit Development Team
==============================================================================
"""

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from analytics.ml_utils import (
    train_risk_model,
    train_credit_model,
    train_segment_model,
    prepare_training_data,
    generate_synthetic_data,
    update_all_predictions,
    MODELS_DIR
)
from analytics.models import MLModelMetadata
from decimal import Decimal


class Command(BaseCommand):
    help = 'Train ShopCredit machine learning models'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--risk',
            action='store_true',
            help='Train only the risk prediction model (Random Forest)'
        )
        parser.add_argument(
            '--credit',
            action='store_true',
            help='Train only the credit limit model (Linear Regression)'
        )
        parser.add_argument(
            '--segment',
            action='store_true',
            help='Train only the segmentation model (K-Means)'
        )
        parser.add_argument(
            '--synthetic',
            action='store_true',
            help='Use synthetic data for training (useful for demo/testing)'
        )
        parser.add_argument(
            '--samples',
            type=int,
            default=100,
            help='Number of synthetic samples to generate (default: 100)'
        )
        parser.add_argument(
            '--update-predictions',
            action='store_true',
            help='Update predictions for all users after training'
        )
    
    def handle(self, *args, **options):
        self.stdout.write(self.style.NOTICE('='*60))
        self.stdout.write(self.style.NOTICE('ShopCredit ML Model Training'))
        self.stdout.write(self.style.NOTICE('='*60))
        
        # Determine which models to train
        train_all = not (options['risk'] or options['credit'] or options['segment'])
        
        # Prepare data
        if options['synthetic']:
            self.stdout.write(self.style.WARNING(
                f"Using synthetic data ({options['samples']} samples)"
            ))
            data = generate_synthetic_data(options['samples'])
        else:
            self.stdout.write('Preparing training data from database...')
            data = prepare_training_data()
            
            if len(data) < 10:
                self.stdout.write(self.style.WARNING(
                    f"Only {len(data)} users found. Adding synthetic data..."
                ))
                synthetic = generate_synthetic_data(100 - len(data))
                import pandas as pd
                data = pd.concat([data, synthetic], ignore_index=True)
        
        self.stdout.write(f'Training data: {len(data)} samples')
        self.stdout.write('')
        
        results = {}
        
        # Train Risk Model
        if train_all or options['risk']:
            self.stdout.write(self.style.NOTICE('Training Risk Prediction Model (Random Forest)...'))
            try:
                model, accuracy, importance = train_risk_model(data)
                results['risk'] = {
                    'accuracy': accuracy,
                    'importance': importance
                }
                
                # Save metadata
                MLModelMetadata.objects.create(
                    model_type='risk_prediction',
                    version=self._get_version('risk_prediction'),
                    file_path=str(MODELS_DIR / 'risk_prediction_model.pkl'),
                    accuracy_score=Decimal(str(accuracy)),
                    training_samples=len(data),
                    is_active=True
                )
                # Deactivate old versions
                MLModelMetadata.objects.filter(
                    model_type='risk_prediction'
                ).exclude(
                    pk=MLModelMetadata.objects.filter(model_type='risk_prediction').latest('training_date').pk
                ).update(is_active=False)
                
                self.stdout.write(self.style.SUCCESS(f'  ✓ Accuracy: {accuracy:.2%}'))
                self.stdout.write('  Feature Importance:')
                for feature, imp in sorted(importance.items(), key=lambda x: -x[1])[:5]:
                    self.stdout.write(f'    - {feature}: {imp:.3f}')
                self.stdout.write('')
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'  [FAILED] Error: {str(e)}'))
        
        # Train Credit Model
        if train_all or options['credit']:
            self.stdout.write(self.style.NOTICE('Training Credit Limit Model (Linear Regression)...'))
            try:
                model, mse, coefficients = train_credit_model(data)
                results['credit'] = {
                    'mse': mse,
                    'coefficients': coefficients
                }
                
                # Save metadata
                MLModelMetadata.objects.create(
                    model_type='credit_limit',
                    version=self._get_version('credit_limit'),
                    file_path=str(MODELS_DIR / 'credit_limit_model.pkl'),
                    accuracy_score=Decimal(str(1 / (1 + mse/10000))),  # Normalize MSE to 0-1
                    training_samples=len(data),
                    is_active=True
                )
                MLModelMetadata.objects.filter(
                    model_type='credit_limit'
                ).exclude(
                    pk=MLModelMetadata.objects.filter(model_type='credit_limit').latest('training_date').pk
                ).update(is_active=False)
                
                self.stdout.write(self.style.SUCCESS(f'  ✓ MSE: {mse:.2f}'))
                self.stdout.write('  Coefficients:')
                for feature, coef in coefficients.items():
                    self.stdout.write(f'    - {feature}: {coef:.4f}')
                self.stdout.write('')
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'  [FAILED] Error: {str(e)}'))
        
        # Train Segment Model
        if train_all or options['segment']:
            self.stdout.write(self.style.NOTICE('Training Shop Segment Model (K-Means)...'))
            try:
                model, scaler, silhouette, centers = train_segment_model(data)
                results['segment'] = {
                    'silhouette': silhouette,
                    'centers': centers
                }
                
                # Save metadata
                MLModelMetadata.objects.create(
                    model_type='shop_segment',
                    version=self._get_version('shop_segment'),
                    file_path=str(MODELS_DIR / 'shop_segment_model.pkl'),
                    accuracy_score=Decimal(str(max(0, silhouette))),
                    training_samples=len(data),
                    is_active=True
                )
                MLModelMetadata.objects.filter(
                    model_type='shop_segment'
                ).exclude(
                    pk=MLModelMetadata.objects.filter(model_type='shop_segment').latest('training_date').pk
                ).update(is_active=False)
                
                self.stdout.write(self.style.SUCCESS(f'  ✓ Silhouette Score: {silhouette:.3f}'))
                self.stdout.write('  Cluster Centers:')
                self.stdout.write(str(centers))
                self.stdout.write('')
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'  [FAILED] Error: {str(e)}'))
        
        # Update predictions if requested
        if options['update_predictions']:
            self.stdout.write(self.style.NOTICE('Updating predictions for all users...'))
            try:
                update_all_predictions()
                self.stdout.write(self.style.SUCCESS('  ✓ Predictions updated'))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'  ✗ Error: {str(e)}'))
        
        # Summary
        self.stdout.write('')
        self.stdout.write(self.style.NOTICE('='*60))
        self.stdout.write(self.style.SUCCESS('Training Complete!'))
        self.stdout.write(f'Models saved to: {MODELS_DIR}')
        self.stdout.write(self.style.NOTICE('='*60))
    
    def _get_version(self, model_type):
        """Get next version number for a model type."""
        latest = MLModelMetadata.objects.filter(
            model_type=model_type
        ).order_by('-version').first()
        
        if latest:
            # Extract version number and increment
            try:
                current = int(latest.version.replace('v', ''))
                return f'v{current + 1}'
            except:
                pass
        
        return 'v1'
