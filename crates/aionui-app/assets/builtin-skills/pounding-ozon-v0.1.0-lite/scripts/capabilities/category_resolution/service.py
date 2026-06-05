#!/usr/bin/env python3
from __future__ import annotations

import re
from typing import Any

from lib.cache_store import read_category_tree_cache
from lib.product_semantics import _flatten_value, detect_product_family
from models.contracts import CategoryResolution, NormalizedProductDraft, RuntimeConfig


def _resolve_runtime_config(config: RuntimeConfig | None = None) -> RuntimeConfig:
    if config is not None:
        return config
    try:
        from lib.config_store import load_config
        return load_config()
    except Exception:
        return RuntimeConfig()


def _walk_leaf_pairs(nodes: list[dict[str, Any]], parent_category_id: int | None = None) -> list[dict[str, Any]]:
    pairs: list[dict[str, Any]] = []
    for node in nodes or []:
        current_category_id = node.get('description_category_id', parent_category_id)
        current_category_name = str(node.get('category_name') or '')
        children = node.get('children') or []
        if node.get('type_id') is not None:
            pairs.append({
                'description_category_id': str(parent_category_id if parent_category_id is not None else current_category_id),
                'category_name': current_category_name,
                'type_id': str(node.get('type_id')),
                'type_name': str(node.get('type_name') or ''),
                'disabled': bool(node.get('disabled')),
            })
        for child in children:
            if child.get('type_id') is not None:
                pairs.append({
                    'description_category_id': str(current_category_id),
                    'category_name': current_category_name,
                    'type_id': str(child.get('type_id')),
                    'type_name': str(child.get('type_name') or ''),
                    'disabled': bool(child.get('disabled')),
                })
            else:
                pairs.extend(_walk_leaf_pairs([child], current_category_id))
    return pairs


def _build_tree_pair_lookup() -> dict[tuple[str, str], dict[str, str]]:
    tree = read_category_tree_cache()
    lookup: dict[tuple[str, str], dict[str, str]] = {}
    for pair in _walk_leaf_pairs(tree.get('result') or []):
        key = (str(pair.get('description_category_id') or ''), str(pair.get('type_id') or ''))
        if key[0] and key[1]:
            lookup[key] = {
                'category_name': str(pair.get('category_name') or ''),
                'type_name': str(pair.get('type_name') or ''),
            }
    return lookup


def _title_signal_terms(title: str) -> list[str]:
    text = str(title or '').strip().lower()
    terms: list[str] = []
    for token in re.split(r'[^\w一-鿿]+', text):
        token = token.strip()
        if len(token) >= 2:
            terms.append(token)
    cjk_text = ''.join(ch for ch in text if '\u4e00' <= ch <= '\u9fff')
    if cjk_text:
        for size in (2, 3, 4):
            for idx in range(0, max(len(cjk_text) - size + 1, 0)):
                token = cjk_text[idx:idx + size]
                if len(token) >= 2:
                    terms.append(token)
    if '保温杯' in text or '保暖杯' in text:
        terms.extend(['保温杯', '保暖杯', '热水瓶'])
    if '水杯' in text:
        terms.extend(['水杯', '杯子'])
    if '吸管杯' in text:
        terms.extend(['吸管杯'])
    if '摇摇杯' in text:
        terms.extend(['摇摇杯'])
    if '咖啡杯' in text or '马克杯' in text:
        terms.extend(['咖啡杯', '马克杯', '杯子'])
    if '收纳' in text or '储物' in text:
        terms.extend(['收纳', '储物', '收纳盒', '储物盒'])
    if '盒' in text:
        terms.extend(['盒', '盒子'])
    if '容器' in text:
        terms.extend(['容器', '食品容器'])
    if '宠物' in text:
        terms.extend(['宠物', '宠物用品', '宠物餐具'])
    if '碗' in text:
        terms.extend(['碗', '宠物碗'])
    if '喂食' in text:
        terms.extend(['喂食', '喂养', '自动喂食器'])
    seen: set[str] = set()
    ordered: list[str] = []
    for item in terms:
        if item in seen:
            continue
        seen.add(item)
        ordered.append(item)
    return ordered


def _category_signal_text(draft: NormalizedProductDraft) -> str:
    parts: list[str] = []
    for value in [
        draft.title,
        draft.attributes.get('sku_title'),
        draft.attributes.get('specification'),
        draft.attributes.get('selected_variant'),
        draft.provenance.get('detail_categories'),
        (draft.attributes.get('detail_parsed') or {}).get('title') if isinstance(draft.attributes.get('detail_parsed'), dict) else None,
        (draft.attributes.get('detail_parsed') or {}).get('categories') if isinstance(draft.attributes.get('detail_parsed'), dict) else None,
    ]:
        parts.extend(_flatten_value(value))

    detail_parsed = draft.attributes.get('detail_parsed') or {}
    if isinstance(detail_parsed, dict):
        cpv_attrs = detail_parsed.get('cpv_attributes') or {}
        if isinstance(cpv_attrs, dict):
            for key in ('产品类别', '品类', '类别'):
                parts.extend(_flatten_value(cpv_attrs.get(key)))
        sku_attrs = detail_parsed.get('sku_attributes') or {}
        if isinstance(sku_attrs, dict):
            for key in ('颜色', '规格'):
                parts.extend(_flatten_value(sku_attrs.get(key)))

    return ' '.join(str(part).strip() for part in parts if str(part).strip())


def _prefer_thermos_cup_over_bottle(
    draft: NormalizedProductDraft,
    description_category_id: str | None,
    type_id: str | None,
) -> tuple[str | None, str | None, bool]:
    title = str(draft.title or '')
    if '保温杯' not in title:
        return description_category_id, type_id, False
    if str(description_category_id or '') == '17027928' and str(type_id or '') == '92576':
        return '17027928', '92574', True
    return description_category_id, type_id, False


def _is_candidate_semantically_compatible(
    draft: NormalizedProductDraft,
    *,
    category_name: str | None,
    type_name: str | None,
) -> bool:
    title = str(draft.title or '').lower()
    haystack = f"{str(category_name or '')} {str(type_name or '')}".lower()
    if not haystack.strip():
        return True
    product_family = detect_product_family(draft)
    thermos_cup_terms = ('保温杯', '保暖杯', '吸管杯', '冰霸杯', '吨吨杯', '水杯')
    thermos_cup_expected_terms = ('термос', 'термокруж', 'круж', '杯', '保暖杯', '保温杯', '吸管杯')
    apparel_conflict_terms = (
        'шапк', '帽', 'cap', 'берет', 'панам', 'шарф', 'перчат', 'вареж', 'плат',
        'аксессуар', 'accessor', 'ремень', 'галст', 'балаклав',
    )
    storage_expected_terms = ('收纳', '储物', '整理', '收纳盒', '储物盒', '置物', 'органайзер', 'контейнер', 'хранен')
    pet_expected_terms = ('宠物', '猫', '狗', '宠物碗', '喂食', '喂养', 'миск', 'корм', 'поил')
    pet_bowl_expected_terms = ('宠物碗', '狗碗', '猫碗', '喂食', 'миск', 'корм', 'поил')
    kitchen_bowl_conflict_terms = ('餐具', '沙拉碗', '糖碗', '汤碗', '茶碗', '酱汁碗')

    if product_family == 'thermos_cup':
        if any(term in haystack for term in apparel_conflict_terms):
            return False
        return any(term in haystack for term in thermos_cup_expected_terms)
    if product_family == 'apparel_accessory':
        if any(term in haystack for term in thermos_cup_expected_terms):
            return False
        return any(term in haystack for term in apparel_conflict_terms)
    if product_family == 'pet':
        if '碗' in title:
            if any(term in haystack for term in kitchen_bowl_conflict_terms):
                return False
            return any(term in haystack for term in pet_bowl_expected_terms)
        return any(term in haystack for term in pet_expected_terms)
    if product_family == 'generic_accessory':
        if any(term in title for term in ('收纳', '储物', '整理', '置物')):
            return any(term in haystack for term in storage_expected_terms)
    if any(term in title for term in thermos_cup_terms):
        if any(term in haystack for term in apparel_conflict_terms):
            return False
        return any(term in haystack for term in thermos_cup_expected_terms)
    return True


def _heuristic_category_candidates(draft: NormalizedProductDraft) -> list[dict[str, Any]]:
    tree = read_category_tree_cache()
    signal_text = _category_signal_text(draft)
    terms = _title_signal_terms(signal_text)
    if not terms:
        return []
    default_thermos_cup_candidate = [{
        'source_category_id': None,
        'description_category_id': '17027928',
        'type_id': '92574',
        'category_name': '用于气泡水的保温瓶、保温杯和虹吸管',
        'type_name': '保暖杯',
        'raw_score': 0.91,
        'confidence': 0.91,
        'match_terms': [term for term in terms if term in {'保温杯', '保暖杯', '吸管杯'}] or ['保温杯'],
    }]
    pairs = [pair for pair in _walk_leaf_pairs(tree.get('result') or []) if not pair.get('disabled')]
    if not pairs and any(token in str(draft.title or '') for token in ['保温杯', '保暖杯', '吸管杯', '吨吨杯', '冰霸杯']):
        return default_thermos_cup_candidate
    scored: list[dict[str, Any]] = []
    for pair in pairs:
        haystack = f"{pair.get('category_name', '')} {pair.get('type_name', '')}".lower()
        score = 0.0
        hits: list[str] = []
        type_name = str(pair.get('type_name') or '')
        category_name = str(pair.get('category_name') or '')
        for term in terms:
            if term.lower() in haystack:
                weight = 0.35
                if term in type_name:
                    weight += 0.20
                if term in category_name:
                    weight += 0.15
                if term in {'保温杯', '保暖杯', '热水瓶', '吸管杯', '摇摇杯', '马克杯', '咖啡杯'}:
                    weight += 0.20
                if '杯' in str(draft.title or '') and '杯' in type_name:
                    weight += 0.18
                if '保温杯' in str(draft.title or '') and type_name == '保暖杯':
                    weight += 0.40
                if '保温杯' in str(draft.title or '') and type_name == '热水瓶':
                    weight -= 0.10
                if '吸管杯' in str(draft.title or '') and type_name == '保暖杯':
                    weight += 0.08
                if term in {'收纳', '储物', '收纳盒', '储物盒'} and ('收纳' in category_name or '收纳' in type_name or '储物' in type_name):
                    weight += 0.35
                if term in {'宠物', '宠物用品', '宠物餐具'} and '宠物' in haystack:
                    weight += 0.35
                if term in {'碗', '宠物碗'} and '宠物碗' in type_name:
                    weight += 0.45
                if term in {'喂食', '喂养'} and ('喂食' in haystack or '喂养' in haystack):
                    weight += 0.25
                score += weight
                hits.append(term)
        if detect_product_family(draft) == 'pet':
            if '碗' in str(draft.title or '') and '宠物碗' in type_name:
                score += 0.55
            if any(token in signal_text for token in ('猫碗', '狗碗', '宠物碗', '狗盆')) and '宠物碗' in type_name:
                score += 1.1
            if any(token in signal_text for token in ('成套自动喂食', '自动喂食')) and '自动喂食器' in type_name:
                score -= 0.9
            if '喂食器' in signal_text and any(token in signal_text for token in ('猫碗', '狗碗', '宠物碗', '狗盆')) and '自动喂食器' in type_name:
                score -= 1.2
            if '宠物' in haystack:
                score += 0.25
            if any(conflict in haystack for conflict in ('餐具', '沙拉碗', '糖碗', '茶碗', '酱汁碗')) and '宠物' not in haystack:
                score -= 0.8
        if detect_product_family(draft) == 'generic_accessory':
            if any(token in signal_text for token in ('收纳', '储物', '整理', '置物')):
                if '收纳' in haystack or '储物' in haystack:
                    score += 0.5
            if '汽车' in signal_text and '汽车' in haystack:
                score += 0.2
            elif '汽车' not in signal_text and '汽车' in haystack:
                score -= 1.1
            if any(token in signal_text for token in ('收纳盒', '储物盒', '桌面收纳盒')) and type_name in {'收纳盒', '储物盒', '文具收纳盒'}:
                score += 0.9
        if score <= 0:
            continue
        scored.append({
            'source_category_id': None,
            'description_category_id': pair['description_category_id'],
            'type_id': pair['type_id'],
            'category_name': pair.get('category_name'),
            'type_name': pair.get('type_name'),
            'raw_score': score,
            'confidence': min(score, 0.99),
            'match_terms': hits,
        })
    scored.sort(
        key=lambda item: (
            float(item.get('raw_score') or 0.0),
            len(item.get('match_terms') or []),
            1 if str(item.get('type_name') or '') == '保暖杯' else 0,
        ),
        reverse=True,
    )
    if not scored and any(token in str(draft.title or '') for token in ['保温杯', '保暖杯', '吸管杯', '吨吨杯', '冰霸杯']):
        return default_thermos_cup_candidate
    return scored[:5]


def resolve_category(
    draft: NormalizedProductDraft,
    category_entries: list[dict[str, Any]],
    config: RuntimeConfig | None = None,
) -> CategoryResolution:
    runtime_config = _resolve_runtime_config(config)
    confidence_threshold = float(runtime_config.category_confidence_threshold)
    margin_threshold = float(runtime_config.category_margin_threshold)

    candidates: list[dict[str, Any]] = []
    rejected_candidates: list[dict[str, Any]] = []
    source_categories = {str(x) for x in draft.source_category_ids}
    tree_pair_lookup = _build_tree_pair_lookup()
    for entry in category_entries:
        source_id = str(entry.get('source_category_id') or '')
        confidence = float(entry.get('confidence') or 0.0)
        if source_id and source_id in source_categories:
            normalized = entry | {'confidence': confidence}
            pair_key = (
                str(normalized.get('description_category_id') or ''),
                str(normalized.get('type_id') or ''),
            )
            tree_names = tree_pair_lookup.get(pair_key) or {}
            if tree_names:
                normalized = normalized | {
                    'category_name': str(normalized.get('category_name') or tree_names.get('category_name') or ''),
                    'type_name': str(normalized.get('type_name') or tree_names.get('type_name') or ''),
                }
            normalized = normalized | {
                'product_family': str(normalized.get('product_family') or detect_product_family(draft)),
            }
            if _is_candidate_semantically_compatible(
                draft,
                category_name=normalized.get('category_name'),
                type_name=normalized.get('type_name'),
            ):
                candidates.append(normalized)
            else:
                rejected_candidates.append(normalized)
    candidates = sorted(candidates, key=lambda x: float(x.get('confidence') or 0.0), reverse=True)

    explanation: dict[str, Any] = {
        'source_category_ids': draft.source_category_ids,
        'threshold': confidence_threshold,
        'margin_threshold': margin_threshold,
    }
    if rejected_candidates:
        explanation['semantic_rejected_cached_candidates'] = [
            {
                'source_category_id': item.get('source_category_id'),
                'description_category_id': item.get('description_category_id'),
                'type_id': item.get('type_id'),
                'category_name': item.get('category_name'),
                'type_name': item.get('type_name'),
            }
            for item in rejected_candidates[:5]
        ]

    if not candidates:
        heuristic = _heuristic_category_candidates(draft)
        if heuristic:
            top = heuristic[0]
            second = heuristic[1] if len(heuristic) > 1 else None
            confidence = float(top.get('confidence') or 0.0)
            margin = confidence - float(second.get('confidence') or 0.0) if second else confidence
            blocked = confidence < confidence_threshold
            if '保温杯' in str(draft.title or '') and str(top.get('type_name') or '') == '保暖杯':
                blocked = False
            explanation.update({
                'margin': margin,
                'blocked': blocked,
                'fallback': 'title_tree_heuristic',
                'title': draft.title,
                'match_terms': top.get('match_terms') or [],
            })
            return CategoryResolution(
                description_category_id=str(top.get('description_category_id')),
                type_id=str(top.get('type_id')),
                confidence=confidence,
                top_candidates=heuristic,
                cache_version='tree-heuristic-v1',
                cache_age_seconds=0,
                explanation=explanation,
            )

    top = candidates[0] if candidates else None
    second = candidates[1] if len(candidates) > 1 else None
    confidence = float(top.get('confidence') or 0.0) if top else 0.0
    margin = confidence - float(second.get('confidence') or 0.0) if second else confidence
    description_category_id = str(top.get('description_category_id')) if top else None
    type_id = str(top.get('type_id')) if top else None
    description_category_id, type_id, corrected = _prefer_thermos_cup_over_bottle(
        draft,
        description_category_id,
        type_id,
    )
    explanation.update({
        'margin': margin,
        'blocked': not top or confidence < confidence_threshold or margin < margin_threshold,
    })
    if corrected:
        explanation['cache_override'] = 'prefer_cup_type_for_thermos_cup_title'
        confidence = max(confidence, 0.91)
    return CategoryResolution(
        description_category_id=description_category_id,
        type_id=type_id,
        confidence=confidence,
        top_candidates=candidates[:5],
        cache_version='1',
        cache_age_seconds=0,
        explanation=explanation,
    )
