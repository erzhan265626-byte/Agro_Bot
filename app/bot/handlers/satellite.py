import os
import io

import requests
import numpy as np
import rasterio
import matplotlib.pyplot as plt

from rasterio.features import geometry_mask
from dotenv import load_dotenv

from aiogram import Router, F
from aiogram.types import (
    Message,
    BufferedInputFile,
    ReplyKeyboardMarkup,
    KeyboardButton
)
from aiogram.fsm.context import FSMContext

from app.bot.keyboards.main_menu import main_menu
from database.field_service import get_all_fields
from database.db import save_satellite_result


router = Router()

load_dotenv()


TOKEN_URL = (
    "https://identity.dataspace.copernicus.eu/"
    "auth/realms/CDSE/protocol/openid-connect/token"
)

PROCESS_URL = (
    "https://sh.dataspace.copernicus.eu/process/v1"
)

CATALOG_URL = (
    "https://sh.dataspace.copernicus.eu/catalog/v1/search"
)


# =========================================================
# COPERNICUS
# =========================================================

def get_copernicus_token():

    client_id = os.getenv(
        "COPERNICUS_CLIENT_ID"
    )

    client_secret = os.getenv(
        "COPERNICUS_CLIENT_SECRET"
    )

    if not client_id or not client_secret:

        raise Exception(
            "COPERNICUS_CLIENT_ID или "
            "COPERNICUS_CLIENT_SECRET "
            "не найдены в .env"
        )

    response = requests.post(
        TOKEN_URL,
        data={
            "grant_type": "client_credentials",
            "client_id": client_id,
            "client_secret": client_secret
        },
        timeout=30
    )

    if response.status_code != 200:

        raise Exception(
            f"Ошибка авторизации Copernicus: "
            f"{response.status_code}\n"
            f"{response.text}"
        )

    return response.json()["access_token"]


# =========================================================
# ГЕОМЕТРИЯ
# =========================================================

def make_polygon(boundary):

    if not boundary or len(boundary) < 3:

        raise Exception(
            "У поля недостаточно точек границы."
        )

    coordinates = []

    for point in boundary:

        latitude = float(point[0])
        longitude = float(point[1])

        coordinates.append([
            longitude,
            latitude
        ])

    if coordinates[0] != coordinates[-1]:

        coordinates.append(
            coordinates[0]
        )

    return {
        "type": "Polygon",
        "coordinates": [
            coordinates
        ]
    }


def get_bbox(boundary):

    lats = [
        float(point[0])
        for point in boundary
    ]

    lons = [
        float(point[1])
        for point in boundary
    ]

    return [
        min(lons),
        min(lats),
        max(lons),
        max(lats)
    ]


# =========================================================
# ПОИСК ПОСЛЕДНЕГО СНИМКА
# =========================================================

def get_latest_sentinel_date(
        token,
        boundary
):

    if not boundary:

        raise Exception(
            "У поля отсутствуют границы."
        )

    bbox = get_bbox(boundary)

    headers = {
        "Authorization":
        f"Bearer {token}",

        "Content-Type":
        "application/json"
    }

    data = {

        "bbox": bbox,

        "datetime": (
            "2026-01-01T00:00:00Z/"
            "2026-12-31T23:59:59Z"
        ),

        "collections": [
            "sentinel-2-l2a"
        ],

        "limit": 20
    }

    response = requests.post(
        CATALOG_URL,
        headers=headers,
        json=data,
        timeout=60
    )

    if response.status_code != 200:

        raise Exception(
            f"Ошибка Catalog API: "
            f"{response.status_code}\n"
            f"{response.text}"
        )

    result = response.json()

    features = result.get(
        "features",
        []
    )

    if not features:

        return None

    dates = []

    for feature in features:

        properties = feature.get(
            "properties",
            {}
        )

        datetime_value = properties.get(
            "datetime"
        )

        if datetime_value:

            dates.append(
                datetime_value[:10]
            )

    if not dates:

        return None

    dates.sort(
        reverse=True
    )

    return dates[0]


# =========================================================
# SENTINEL-2 NDVI + NDMI
# =========================================================

def get_satellite_data(
        token,
        boundary,
        date
):

    geometry = make_polygon(
        boundary
    )

    bbox = get_bbox(boundary)

    evalscript = """
//VERSION=3

function setup() {

    return {
        input: [
            {
                bands: [
                    "B04",
                    "B08",
                    "B11",
                    "dataMask"
                ],
                units: "REFLECTANCE"
            }
        ],

        output: {
            id: "default",
            bands: 3,
            sampleType: SampleType.FLOAT32
        }
    }
}

function evaluatePixel(sample) {

    if (sample.dataMask == 0) {

        return [
            0,
            0,
            0
        ];
    }

    let ndvi = 0;
    let ndmi = 0;

    let ndviDenominator =
        sample.B08 + sample.B04;

    if (ndviDenominator != 0) {

        ndvi =
            (sample.B08 - sample.B04)
            / ndviDenominator;
    }

    let ndmiDenominator =
        sample.B08 + sample.B11;

    if (ndmiDenominator != 0) {

        ndmi =
            (sample.B08 - sample.B11)
            / ndmiDenominator;
    }

    return [
        ndvi,
        ndmi,
        sample.dataMask
    ];
}
"""

    request_data = {

        "input": {

            "bounds": {

                "bbox": bbox,

                "properties": {
                    "crs":
                    "http://www.opengis.net/def/crs/OGC/1.3/CRS84"
                },

                "geometry": geometry
            },

            "data": [

                {
                    "type":
                    "sentinel-2-l2a",

                    "dataFilter": {

                        "timeRange": {

                            "from":
                            f"{date}T00:00:00Z",

                            "to":
                            f"{date}T23:59:59Z"
                        },

                        "mosaickingOrder":
                        "leastCC"
                    },

                    "processing": {

                        "harmonizeValues":
                        True
                    }
                }
            ]
        },

        "output": {

            "width": 700,

            "height": 700,

            "responses": [

                {
                    "identifier":
                    "default",

                    "format": {
                        "type":
                        "image/tiff"
                    }
                }
            ]
        },

        "evalscript":
        evalscript
    }

    headers = {

        "Authorization":
        f"Bearer {token}",

        "Content-Type":
        "application/json"
    }

    response = requests.post(
        PROCESS_URL,
        headers=headers,
        json=request_data,
        timeout=120
    )

    if response.status_code != 200:

        raise Exception(
            f"Ошибка Process API: "
            f"{response.status_code}\n"
            f"{response.text}"
        )

    return response.content


# =========================================================
# ОБРАБОТКА RASTER
# =========================================================

def prepare_data(
        tiff_data,
        boundary
):

    with rasterio.open(
        io.BytesIO(tiff_data)
    ) as dataset:

        ndvi = dataset.read(1)

        ndmi = dataset.read(2)

        data_mask = dataset.read(3)

        transform = dataset.transform

        bounds = dataset.bounds

    ndvi = np.asarray(
        ndvi,
        dtype=np.float32
    )

    ndmi = np.asarray(
        ndmi,
        dtype=np.float32
    )

    data_mask = np.asarray(
        data_mask,
        dtype=np.float32
    )

    polygon = make_polygon(
        boundary
    )

    inside_polygon = geometry_mask(
        [polygon],
        transform=transform,
        invert=True,
        out_shape=ndvi.shape
    )

    valid_ndvi = (
        inside_polygon
        &
        (data_mask > 0)
        &
        np.isfinite(ndvi)
        &
        (ndvi >= -1)
        &
        (ndvi <= 1)
    )

    valid_ndmi = (
        inside_polygon
        &
        (data_mask > 0)
        &
        np.isfinite(ndmi)
        &
        (ndmi >= -1)
        &
        (ndmi <= 1)
    )

    if not np.any(valid_ndvi):

        raise Exception(
            "Внутри границы поля "
            "нет корректных NDVI-данных."
        )

    if not np.any(valid_ndmi):

        raise Exception(
            "Внутри границы поля "
            "нет корректных NDMI-данных."
        )

    masked_ndvi = np.where(
        valid_ndvi,
        ndvi,
        np.nan
    )

    masked_ndmi = np.where(
        valid_ndmi,
        ndmi,
        np.nan
    )

    return (
        masked_ndvi,
        masked_ndmi,
        bounds
    )


# =========================================================
# NDVI КАРТА
# =========================================================

def create_ndvi_map(
        masked_ndvi,
        boundary,
        field_name,
        date,
        bounds
):

    values = masked_ndvi[
        np.isfinite(masked_ndvi)
    ]

    mean_ndvi = float(
        np.mean(values)
    )

    min_ndvi = float(
        np.min(values)
    )

    max_ndvi = float(
        np.max(values)
    )

    polygon_lon = [
        float(point[1])
        for point in boundary
    ]

    polygon_lat = [
        float(point[0])
        for point in boundary
    ]

    polygon_lon.append(
        polygon_lon[0]
    )

    polygon_lat.append(
        polygon_lat[0]
    )

    fig, ax = plt.subplots(
        figsize=(10, 8)
    )

    image = ax.imshow(
        masked_ndvi,
        cmap="RdYlGn",
        vmin=-1,
        vmax=1,
        extent=[
            bounds.left,
            bounds.right,
            bounds.bottom,
            bounds.top
        ],
        origin="upper"
    )

    ax.plot(
        polygon_lon,
        polygon_lat,
        linewidth=2.5
    )

    ax.fill(
        polygon_lon,
        polygon_lat,
        alpha=0.08
    )

    ax.set_title(
        f"AgroAI — NDVI\n"
        f"{field_name} | {date}"
    )

    ax.set_xlabel(
        "Долгота"
    )

    ax.set_ylabel(
        "Широта"
    )

    colorbar = fig.colorbar(
        image,
        ax=ax
    )

    colorbar.set_label(
        "NDVI"
    )

    ax.grid(
        True,
        alpha=0.25
    )

    fig.tight_layout()

    buffer = io.BytesIO()

    fig.savefig(
        buffer,
        format="png",
        dpi=160,
        bbox_inches="tight"
    )

    plt.close(fig)

    buffer.seek(0)

    return (
        buffer.read(),
        mean_ndvi,
        min_ndvi,
        max_ndvi
    )


# =========================================================
# NDMI КАРТА
# =========================================================

def create_ndmi_map(
        masked_ndmi,
        boundary,
        field_name,
        date,
        bounds
):

    values = masked_ndmi[
        np.isfinite(masked_ndmi)
    ]

    mean_ndmi = float(
        np.mean(values)
    )

    min_ndmi = float(
        np.min(values)
    )

    max_ndmi = float(
        np.max(values)
    )

    polygon_lon = [
        float(point[1])
        for point in boundary
    ]

    polygon_lat = [
        float(point[0])
        for point in boundary
    ]

    polygon_lon.append(
        polygon_lon[0]
    )

    polygon_lat.append(
        polygon_lat[0]
    )

    fig, ax = plt.subplots(
        figsize=(10, 8)
    )

    image = ax.imshow(
        masked_ndmi,
        cmap="BrBG",
        vmin=-1,
        vmax=1,
        extent=[
            bounds.left,
            bounds.right,
            bounds.bottom,
            bounds.top
        ],
        origin="upper"
    )

    ax.plot(
        polygon_lon,
        polygon_lat,
        linewidth=2.5
    )

    ax.fill(
        polygon_lon,
        polygon_lat,
        alpha=0.08
    )

    ax.set_title(
        f"AgroAI — NDMI\n"
        f"{field_name} | {date}"
    )

    ax.set_xlabel(
        "Долгота"
    )

    ax.set_ylabel(
        "Широта"
    )

    colorbar = fig.colorbar(
        image,
        ax=ax
    )

    colorbar.set_label(
        "NDMI"
    )

    ax.grid(
        True,
        alpha=0.25
    )

    fig.tight_layout()

    buffer = io.BytesIO()

    fig.savefig(
        buffer,
        format="png",
        dpi=160,
        bbox_inches="tight"
    )

    plt.close(fig)

    buffer.seek(0)

    return (
        buffer.read(),
        mean_ndmi,
        min_ndmi,
        max_ndmi
    )


# =========================================================
# ОЦЕНКА NDVI
# =========================================================

def get_ndvi_condition(ndvi):

    if ndvi < 0:

        return (
            "🔵 Вода, снег или "
            "нерастительная поверхность."
        )

    if ndvi < 0.2:

        return (
            "🔴 Очень слабая "
            "растительность."
        )

    if ndvi < 0.3:

        return (
            "🟡 Слабая или умеренная "
            "растительность."
        )

    if ndvi < 0.5:

        return (
            "🟢 Умеренная "
            "растительность."
        )

    if ndvi < 0.7:

        return (
            "🟢 Хорошая "
            "растительность."
        )

    return (
        "🟢 Очень высокая "
        "растительность."
    )


# =========================================================
# ОЦЕНКА NDMI
# =========================================================

def get_ndmi_condition(ndmi):

    if ndmi < -0.3:

        return (
            "🔴 Очень низкая влажность "
            "растительности."
        )

    if ndmi < 0:

        return (
            "🟠 Низкая влажность "
            "растительности."
        )

    if ndmi < 0.2:

        return (
            "🟡 Умеренная влажность "
            "растительности."
        )

    if ndmi < 0.4:

        return (
            "🟢 Хорошая влажность "
            "растительности."
        )

    return (
        "🟢 Высокая влажность "
        "растительности."
    )


# =========================================================
# ВЫБОР ПОЛЯ
# =========================================================

@router.message(
    F.text == "🛰 Спутниковый анализ"
)
async def satellite_start(
        message: Message,
        state: FSMContext
):

    # ID пользователя Telegram
    user_id = message.from_user.id

    # Получаем только поля этого пользователя
    fields = get_all_fields(user_id)

    if not fields:

        await message.answer(
            "🛰 Для спутникового анализа "
            "сначала зарегистрируйте поле.",
            reply_markup=main_menu
        )

        return

    keyboard = []

    for field in fields:

        keyboard.append([
            KeyboardButton(
                text=(
                    f"🛰 {field.name} — "
                    f"{field.crop}"
                )
            )
        ])

    keyboard.append([
        KeyboardButton(
            text="🔙 Назад"
        )
    ])

    satellite_keyboard = ReplyKeyboardMarkup(
        keyboard=keyboard,
        resize_keyboard=True
    )

    await state.update_data(
        satellite_select=True
    )

    await message.answer(
        "🛰 Выберите поле для "
        "спутникового анализа:",
        reply_markup=satellite_keyboard
    )


# =========================================================
# СПУТНИКОВЫЙ АНАЛИЗ
# =========================================================

@router.message(
    F.text.startswith("🛰 ")
)
async def satellite_field_selected(
        message: Message,
        state: FSMContext
):

    # ID пользователя Telegram
    user_id = message.from_user.id

    # Получаем только поля этого пользователя
    fields = get_all_fields(user_id)

    selected_field = None

    try:

        # Например:
        # 🛰 Shroud — Пшеница
        text = message.text.replace(
            "🛰 ",
            "",
            1
        ).strip()

        for field in fields:

            button_text = (
                f"{field.name} — "
                f"{field.crop}"
            )

            if text == button_text:

                selected_field = field

                break

    except Exception as error:

        print(
            "Ошибка определения поля:",
            error
        )

        selected_field = None

    if selected_field is None:

        await message.answer(
            "❌ Поле не найдено."
        )

        return

    field = selected_field

    await state.clear()

    await message.answer(
        "🛰 Начинаю спутниковый анализ...\n\n"
        f"🌾 Поле: {field.name}\n"
        f"🌱 Культура: {field.crop}\n"
        f"📐 Площадь: {field.area} га\n\n"
        "🔐 Подключение к Copernicus..."
    )

    try:

        # -------------------------------------------------
        # COPERNICUS
        # -------------------------------------------------

        token = get_copernicus_token()

        await message.answer(
            "✅ Copernicus подключён.\n\n"
            "🛰 Поиск последнего "
            "доступного снимка Sentinel-2..."
        )

        # -------------------------------------------------
        # ДАТА
        # -------------------------------------------------

        date = get_latest_sentinel_date(
            token,
            field.boundary
        )

        if not date:

            await message.answer(
                "❌ Для данного поля "
                "не найден снимок Sentinel-2.",
                reply_markup=main_menu
            )

            return

        await message.answer(
            "📅 Последний снимок найден:\n"
            f"{date}\n\n"
            "🧮 Рассчитываю NDVI и NDMI..."
        )

        # -------------------------------------------------
        # SENTINEL DATA
        # -------------------------------------------------

        tiff_data = get_satellite_data(
            token,
            field.boundary,
            date
        )

        await message.answer(
            "📊 Данные Sentinel-2 получены."
        )

        # -------------------------------------------------
        # PROCESS
        # -------------------------------------------------

        (
            masked_ndvi,
            masked_ndmi,
            bounds
        ) = prepare_data(
            tiff_data,
            field.boundary
        )

        # -------------------------------------------------
        # NDVI
        # -------------------------------------------------

        await message.answer(
            "🧮 Обрабатываю NDVI..."
        )

        (
            ndvi_image,
            mean_ndvi,
            min_ndvi,
            max_ndvi
        ) = create_ndvi_map(
            masked_ndvi,
            field.boundary,
            field.name,
            date,
            bounds
        )

        ndvi_condition = get_ndvi_condition(
            mean_ndvi
        )

        ndvi_photo = BufferedInputFile(
            ndvi_image,
            filename="agroai_ndvi_map.png"
        )

        await message.answer_photo(
            photo=ndvi_photo,
            caption=(
                f"🛰 <b>NDVI-карта поля</b>\n\n"
                f"🌾 Поле: {field.name}\n"
                f"🌱 Культура: {field.crop}\n"
                f"📐 Площадь: {field.area} га\n"
                f"📅 Снимок: {date}\n\n"
                f"🌿 Средний NDVI: "
                f"{mean_ndvi:.3f}\n"
                f"📉 Минимальный NDVI: "
                f"{min_ndvi:.3f}\n"
                f"📈 Максимальный NDVI: "
                f"{max_ndvi:.3f}\n\n"
                f"{ndvi_condition}"
            ),
            parse_mode="HTML"
        )

        # -------------------------------------------------
        # NDMI
        # -------------------------------------------------

        await message.answer(
            "💧 Обрабатываю NDMI..."
        )

        (
            ndmi_image,
            mean_ndmi,
            min_ndmi,
            max_ndmi
        ) = create_ndmi_map(
            masked_ndmi,
            field.boundary,
            field.name,
            date,
            bounds
        )

        ndmi_condition = get_ndmi_condition(
            mean_ndmi
        )

        # -------------------------------------------------
        # СОХРАНЕНИЕ РЕЗУЛЬТАТОВ
        # -------------------------------------------------

        save_satellite_result(
            field_id=field.id,
            user_id=user_id,
            date=date,
            mean_ndvi=mean_ndvi,
            min_ndvi=min_ndvi,
            max_ndvi=max_ndvi,
            mean_ndmi=mean_ndmi,
            min_ndmi=min_ndmi,
            max_ndmi=max_ndmi
        )

        print(
            "Результаты спутникового анализа "
            "сохранены в БД."
        )

        ndmi_photo = BufferedInputFile(
            ndmi_image,
            filename="agroai_ndmi_map.png"
        )

        await message.answer_photo(
            photo=ndmi_photo,
            caption=(
                f"💧 <b>NDMI-карта поля</b>\n\n"
                f"🌾 Поле: {field.name}\n"
                f"🌱 Культура: {field.crop}\n"
                f"📐 Площадь: {field.area} га\n"
                f"📅 Снимок: {date}\n\n"
                f"💧 Средний NDMI: "
                f"{mean_ndmi:.3f}\n"
                f"📉 Минимальный NDMI: "
                f"{min_ndmi:.3f}\n"
                f"📈 Максимальный NDMI: "
                f"{max_ndmi:.3f}\n\n"
                f"{ndmi_condition}"
            ),
            parse_mode="HTML"
        )

        # -------------------------------------------------
        # FINISH
        # -------------------------------------------------

        await message.answer(
            "✅ Спутниковый анализ завершён.\n\n"
            "🛰 NDVI — состояние растительности\n"
            "💧 NDMI — влажность растительности\n\n"
            "💾 Результаты сохранены для "
            "последующей сводки поля.",
            reply_markup=main_menu
        )

    except Exception as error:

        print(
            "ОШИБКА СПУТНИКОВОГО АНАЛИЗА:"
        )

        print(error)

        await message.answer(
            "❌ Ошибка спутникового анализа.\n\n"
            f"{str(error)[:1500]}",
            reply_markup=main_menu
        )


# =========================================================
# НАЗАД
# =========================================================

@router.message(
    F.text == "🔙 Назад"
)
async def satellite_back(
        message: Message,
        state: FSMContext
):

    await state.clear()

    await message.answer(
        "🏠 Главное меню",
        reply_markup=main_menu
    )