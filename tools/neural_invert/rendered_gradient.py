"""Finite secant estimates from actual rendered losses, not exact derivatives."""
import math


def slope(low_loss, high_loss, low_unit, high_unit):
    if not all(math.isfinite(v) for v in (low_loss, high_loss, low_unit, high_unit)) or high_unit <= low_unit:
        raise ValueError('Finite losses and positive actual displacement required')
    return (high_loss-low_loss)/(high_unit-low_unit)
