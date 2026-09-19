#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
WELearn GUI — 图形化挂时长工具

依赖：
    pip install requests
    pip install playwright && playwright install chromium   # 仅"自动登录"需要

功能：
    · Playwright 弹浏览器自动登录（可处理滑块）并保存 cookies.json
    · 自动从 cookies.json / welearn_cookie.txt / 手动粘贴 三种方式读 cookie
    · 自动探测 uid / classid / username
    · 挂时长：只发心跳，不写 interactions / score（避免分数被清）
    · 支持按单元 / 全量 / 自定义 SCO 列表
    · 实时日志 + 一键停止
"""

import base64
import json
import os
import queue
import re
import sys
import threading
import time
import traceback
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import urlparse, parse_qs, unquote, quote_plus

import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import random

import requests

# ============================================================
# 常量
# ============================================================
BASE = "https://welearn.sflep.com"
SSO  = "https://sso.sflep.com"
COOKIE_JSON_FILE = "cookies.json"
COOKIE_TXT_FILE  = "welearn_cookie.txt"
SCOS_CACHE_FILE = "scos_cache.json"
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/153.0.0.0 Safari/537.36 Edg/153.0.0.0")


# 下面的是全新版大学英语视听说教程4的单元对应的 SCO 列表，供按单元挂时长使用。
BOOKINFO_UNITS = {
    1: ["a9134f45-ec71-4c37-a099-ed7861546469", "fc78f64b-1e00-49c4-a3a2-24c80fde6853",
        "fc54ab93-6c91-46eb-86df-505bb2df7fd0", "a5b87a53-63ee-479f-b637-0f9341839731",
        "f196b966-e8b1-4805-9208-ffd38a204368", "7dcd60e5-b7c4-4e0e-b5b5-da7f86566530",
        "d8921c34-fe85-4f10-bfd4-64f31822ce13", "d5118802-3c12-48a9-b315-baab0ba55d2d",
        "1682e0ca-141f-4449-8e9d-8475a5b12f89", "33b97262-d311-4e10-ab2f-89472e43ab43",
        "84293694-5d8f-4e2f-ba0b-8a60efbe0ce2", "a0a3002d-7964-47b1-8fe9-c60f7ad1e3c3",
        "8a3c0afa-b490-431e-b5ef-1309f2a8f227", "3367817a-7636-4fa9-90fe-89ae040b7947",
        "229b33bd-6661-434d-b9a0-31a4247e91e3", "0ae711a3-26cd-42e0-bc77-fd92e82c310e",
        "3ea7a36e-0cb4-4a81-b976-44918d9f42a9", "03107424-6198-4e94-a214-61a42077b790",
        "db95209f-f1e1-445c-854e-12fe4c57b31c", "3cfb7e94-3eae-47ca-88ee-81f1c58d9dd5",
        "db3ae779-d0b4-4696-895d-b166e9558fff", "04a05bca-d1da-4ad6-a5cf-6269dcffcb5c",
        "a4f4587b-4478-409b-b8f9-4f3901bf16da", "b5544f5f-ecef-479d-a139-ac09c5c0e9ea",
        "8f7fd936-2b64-4d5c-98ff-00a17fa8e080", "cae0250f-dba8-4f3b-8f9a-b4eb574e0804",
        "f6e83ca8-1a2f-43ba-988d-a7df3e770e63", "553b6fe1-6d46-461b-a6b5-f39e62788d5f",
        "0266f63d-d6b1-4304-938e-69aad8961d69", "901891c0-2485-4c37-b7fc-26be4ed4c350",
        "1fa7191b-416b-4ca2-a9bc-fab2e26edf15", "c7c38eb3-f341-499d-9349-5a9d274f2e50",
        "9ac15a62-4abd-4746-8103-760cf9ba07e3"],
    2: ["d99cd4ef-deef-43ae-a16e-262d4a7c35c8", "b80c8af7-a4e1-4ca9-a693-7774835bd9fe",
        "fd3da42a-1f6b-41a4-a988-92885a6e4592", "d73b987c-0351-4728-842a-cd33c3ed4892",
        "a3ec2c5f-ef4c-452f-99b6-88895ba59be5", "13e226ea-1e26-4ead-bed5-712d884711f1",
        "e6c19f7e-fbe5-4cc8-88b6-6ecf36e341e7", "e6b72b28-9cc2-45ce-bb4b-03eb44a2a673",
        "c9709155-0668-4bba-a4fd-88b30259e6b6", "767fdba8-61ac-4aaa-9405-715317928d02",
        "98b238a4-d32d-49f6-acc3-ebe830f736f2", "b49c8e89-ce13-4117-89a3-9e8bc24c04a2",
        "d6994c5c-99bb-4004-b959-f7676dd0314d", "8233bd87-4308-424d-89fc-d761e5087523",
        "a03cc1f5-066c-43ad-bb8e-cf2c5f9186e2", "e2aaee64-0cf7-4448-9525-7b56b2627155",
        "e2cc6cb4-4d7f-46d1-ac6a-a9c62efd7c87", "4fa97488-32c2-4fca-afec-f5fd73557e9d",
        "6540adbf-b780-4981-9873-42a0e6a12eaa", "59020952-1f59-4954-a4af-df2ddcb15bb7",
        "a892c100-76f7-4dde-b15b-aa632aec84cf", "1c351525-4a8c-4a89-a460-5ed7693ee376",
        "684d6d7c-3612-4b5c-8ccf-15cfa57135eb", "288cefd4-2c14-46e1-bac4-d123dc1b0d45",
        "d408eead-10af-4436-a117-e207a1b8c456", "9a9e6dca-67e8-460f-acae-cff54d2fa4ca",
        "13c1e71b-0f45-48ec-b0ad-8ba66b5db057", "47cb49e3-8cca-41a8-86d8-563d5b51421a",
        "e30d3553-40f4-43cb-a66d-96dd0b1d4153", "0aad3fb7-b69c-4f8e-8d6a-fb45f14af891",
        "4984d077-b7ad-4fee-9232-cd951d877365", "6bf44481-e6f1-4554-87df-ec38126bf2e3",
        "799c8327-8485-476d-b7c9-02639447fc36", "f5aa57dc-f662-4589-adfb-6980c41ad116",
        "e2840437-6a40-4679-87d1-2771f6cfc64f"],
    3: ["ba37a110-b271-4a8d-b8d6-0e03f514573f", "5a98232b-cab1-4723-bc56-643c540c605b",
        "3caa08d1-ed8f-474b-b886-8beceb742b43", "6224c177-2722-4f11-964c-104215610634",
        "4bf0cf3e-c761-4557-8708-0b491f4b521e", "948cec7c-03d7-49a3-9abc-448adec04e6c",
        "e5c23685-368d-4e67-97f4-328c25463b2f", "134fb7c9-608e-4f8b-9a21-bb12aee16e03",
        "c44fc461-a71b-4374-9653-9f383e4f5fee", "6d212e58-4bbb-42dc-9118-b9f271aefa2b",
        "79cc8cc5-6522-4cae-a331-3d585be5a5d7", "888b4fa4-5bd8-4c6f-90c3-1eec7188c0a2",
        "1030a4c6-c540-4225-89a1-e5e27066da5f", "23c0bcb1-05bd-4016-aa13-fac2f51571cc",
        "4d0f9e8d-396a-4acf-a968-72fde041e523", "ccbac864-613e-476e-a747-2e6f0a1004e9",
        "2a99a0da-9c2e-43a2-b5d8-67c20b171ad0", "2f50430c-2c87-44a8-a3fb-8a8c0aa4b874",
        "6ecb1bb2-7120-4d5f-a221-4378c72e1bf2", "96c969b9-8620-4048-9fa8-e3e0cc6d3bf1",
        "9e1944b8-d9ed-4076-8cfc-6c00e6f5ec8f", "60f305ec-de07-4c36-82f3-912eaa4f25b0",
        "69b2bac8-1839-43fc-a91f-5bb5edff6e0c", "08c12561-67f1-4ec1-8bbc-5825e687f118",
        "bba42d40-f40c-4f6c-b812-a13533db44d4", "ac6badfe-6206-438c-8cd9-792546389260",
        "d2f14f81-83af-4516-8e11-2477cc8b7391", "60e4869e-be5d-4c94-9574-8149fd58d1a8",
        "717c4871-a059-4c8b-9436-90ab6130815f", "85b5c263-0d60-44dc-b83e-096c7d788e03",
        "dc6a76c3-332d-423e-813e-1227ecde17ce", "9235e64d-96c1-4ee5-b4b4-40d1ad371343",
        "1dad58f6-2bd3-4197-8906-90b3999b5c19", "5d5c3a1e-0b25-481a-9159-dd62a996e270",
        "b4eb32b0-57e4-4a69-93d6-201c86d96f20", "378a4b37-07c6-433a-853d-b03b5d7ebfb0",
        "3367711f-e7fa-4571-acdd-acf73702fe3e"],
    4: ["dde1ea20-ec92-4492-a5ec-37ce27dc0edb", "348342a2-d9dd-4d79-b25c-34ed82d9389f",
        "55a6aa6c-8388-4f24-8fb5-9b935ed6b667", "e085af37-7e3e-4dc7-833f-276359a26c58",
        "00260018-2cfe-403a-8102-788c52211bd9", "11ec00d9-7b04-4a14-b645-526b4833c4f4",
        "3d51f5c2-a15f-4567-99d6-78ca05b3300e", "6e5868f0-2eb4-4d97-837b-d5d419d6ebbf",
        "526784a7-755b-40f3-98c3-929f1de9ddc2", "f2d22941-516f-4ecc-bd75-0ce75c45df2e",
        "722b2022-afba-49ef-9579-d776bcbf6404", "64211208-b707-4662-a081-7d6bc80ef6c8",
        "231c55cc-ddf2-4f43-a16e-040a28e5ea66", "93e4067e-cdbc-4fae-91cb-3ee71bf7e499",
        "417b0248-fe0e-4588-849c-59af77a4d746", "13d02cbe-d575-42fc-9e60-d801846eb82d",
        "acbfdbe9-cd55-421c-9b18-99870c08bfab", "68f6eece-7470-458d-9ccf-e0b696e65756",
        "e6c2df66-3294-4f4c-9329-7ecce7979f44", "104afebf-6da3-413a-a6c3-e2ab24219b55",
        "97ba0c37-105f-4964-806f-63ae2b8b234a", "5fc5c9ed-86bb-47b5-bb1f-edbe80fc09da",
        "c93f65c7-45d1-44a2-a3ea-6d4cde7eb1e7", "4c37accb-c016-4fb1-9653-be39fa408e99",
        "e1eb5e5c-b03c-4b59-b624-8642bba37a02", "1b5b3ab3-eba0-4e9f-b6b6-e8ed96af81d1",
        "25d6f768-79f6-40ec-8fd7-ad0bbcf9f12d", "829c059f-3c84-4528-b259-9207ac4cbdef",
        "a9b3acd7-be74-4a86-9395-ccb0cb459fc8", "8fd47055-eda2-4378-a62c-44a07ea73756",
        "747b72f4-6a4e-431d-8bb4-47fb8d05d942", "eed4b3ca-e74e-4a7b-9a8d-61f6ab6c933b",
        "74310108-7f92-4b90-baca-820ef8c49869"],
    5: ["5be21f31-6b08-4758-88b7-41643fe7707a", "f0389520-c0aa-4115-ba48-21cf3be204c0",
        "dd7979e1-6911-42f8-b556-8466003c56c1", "2311cd57-b2f3-4ece-b642-882bf38883b8",
        "965dc03a-86db-435c-b49f-09739511b1a3", "cfe32b5c-0751-461e-bbe8-c3b98611b388",
        "d249cc83-d02c-4eba-92a0-d48e923443f5", "0da3da5d-7ed2-4ed2-94da-51dd2039bd7f",
        "d128a352-f5cf-468b-a20c-a5c2800f2edd", "dbd2d1b9-2b97-4550-8c70-e405cf8bae41",
        "6453a5c2-0410-4956-8672-35aee28ac77e", "af75fb98-29ad-4cd8-8853-8a79ac8eba2e",
        "1c76ec24-a4ee-4c51-9e35-f74ffcad15e1", "a7e8ebf9-e39b-4e10-97f5-54ca634fea13",
        "3b64450c-37cf-477f-a3ef-2f25233aa31d", "90ba0b1b-089d-4c32-975f-c64932d75598",
        "1756e663-a7ad-4367-ade8-de7e5e14acac", "12b86587-cc49-4ef7-86ee-c88d4ca9240d",
        "78b8fe86-5660-4261-843d-9248d086b4da", "86cdaba9-ef93-4478-b3e3-c2a2f0e6285e",
        "ecec2754-2a0a-48ae-9b6e-e748e2509ace", "8ec42305-5ea2-4b00-af20-481f82e4a7dc",
        "566e9ef0-3dee-466b-b669-f5fc18e806db", "6df27bce-841f-427f-8443-404c108a0a93",
        "d0d97929-5abb-4207-9fea-c624bf91ca2c", "98e734ae-2995-4dd8-9774-641e922ecf9e",
        "78312708-8633-4901-980f-2c1e314546ef", "62236372-7605-48df-a1a6-ae49555cf440",
        "d0096ed5-e208-4f75-ba36-e4579de394b0", "c223bd61-40c4-4f68-9a98-b7410c4ca5a7",
        "7aaefea4-e46a-4e60-b9d0-64ad5967bc8d", "63abc75a-5e0d-4689-bec8-e8c29202fcb4",
        "aaca0961-d4a5-4e51-becd-9b133c30d52a", "e2334dac-ba8b-4ecf-ad58-ba7f7d21d685"],
    6: ["1eca6474-ec57-4892-8a93-add865026e93", "27cb70a0-ad07-46b2-97fa-abdaef7f0040",
        "2e17f52d-275d-4033-8c30-4e376abd49b9", "9554590e-f099-45fb-b2aa-8b0ac5cc02f2",
        "ee1e12e6-3f8e-43cf-bc7a-3e0109194771", "6d466f58-e205-4156-8a04-24a36b9c52b1",
        "839478a2-c5dc-4b0a-8e27-be35a4c18acf", "93f5c944-55d3-4b0f-8fe3-d0429c86d5ac",
        "b85fc762-6db7-4c49-ab6d-4e2afbbc6ffc", "db08b937-59c7-465c-9baa-16636653e2d3",
        "666737b6-882f-4032-ac0f-e72a11292ec4", "6f9d2a73-5b87-4e39-a89d-c8432b95c68b",
        "1ac52be3-de64-4a64-9ada-bef92c259a54", "1974f4b2-35b0-48a3-b1f4-af557028d7e8",
        "7855b0be-ad59-43ac-995a-bda1934152cb", "b3a82937-10e3-4de6-b593-59df10e666a0",
        "b72f990c-5964-48c5-8fa2-c68e1b86ace1", "a947707c-2fb4-4535-9a71-517cf2a316b6",
        "1526a25d-7325-4d88-b3f8-c67c2e68ce4b", "c6845de9-79ff-44b1-aa27-a98a9536fec7",
        "468afc4c-396b-4724-b9ae-ae5286effdf8", "fd108b30-55d3-4592-8fc1-d9f09b9dfa36",
        "42ca08b8-d45c-41d0-8d2c-dc37ecd1d490", "163294be-fce0-44cb-94fb-df12f33b8f80",
        "bfc9b77b-ca2d-4218-86ff-6dc8f8dc2fda", "ab53b539-0364-4dbb-9158-075bac519c2d",
        "a94718d8-743c-4523-a5d1-319f07ba3e7b", "2b62be47-492b-4979-b237-69c410e67807",
        "a88f5ca2-adae-4a21-897f-cba85771f44f", "201a85f6-6df6-4c91-bd24-e83fba33e389",
        "11aa2bdd-1b96-4cf6-a3ff-bcca9c705d7a", "633045c8-ba8f-487d-8a16-b2f674c59bdd",
        "b75ae546-8b45-43aa-8bac-3cceefe64ff7", "f6824498-8dc8-40b2-9325-a947e1a7c5f4",
        "14f540e3-f259-47e7-93ad-5c30c5003042", "f57984b9-aa52-4345-9f77-88ea4bf3ae6b"],
    7: ["6bdae561-d302-45eb-a0a8-05cf017c3de7", "59b7efcb-7e30-4c9f-83af-a7e7b2f2cc59",
        "5fd27daa-d3b7-4725-97aa-b73555ce28e5", "21d585ee-5b3c-4b80-8200-25da091ade3b",
        "61b3111b-c734-4b1c-a836-afd2f8a2527b", "8f3385e1-d90f-4c13-a42f-c1f3183c59e2",
        "1e0573b7-1281-464b-8f73-79cbfbf10005", "f19a4189-1c71-4e7b-837b-a1c7807f6745",
        "c880daab-6675-4058-9143-8b5efd05eea6", "6fed4794-5d27-4664-8972-1b17c0b9b0fe",
        "1f8dc28a-31ff-42c5-aef4-c9c6331e012f", "97babecd-9424-4804-8502-565f356e2d38",
        "045a1684-5859-40f7-8004-6444b3931d72", "9c061a99-fabb-4048-8c11-01e03ddfa6a6",
        "baaef5bd-19a6-4a06-b0fb-5dcc0c2f526e", "02bcc8eb-9e5f-4c2b-aefc-03246f24e064",
        "50c6ce0d-87b0-4fa0-beef-ee49181123ff", "8c0e5f96-cf13-4306-937a-f04780d7f073",
        "741f598e-6771-46c9-985f-4da19e457fda", "32aad8e4-5a98-4451-a3a3-d633b071c67a",
        "d48acb4b-0e91-4526-b77b-a4006a28cdb2", "01b460ff-8e6c-48cf-a155-2c364b5cb4d3",
        "a16bb77a-c745-48da-b51c-4b9147b66b38", "7b6710a1-0ea4-4ba2-b804-b0b2e9a228a8",
        "2f943f9b-c8a4-400d-a89c-feb9e3761d6f", "c80f9784-4c23-47fd-bb99-051939c75b4d",
        "8257cd7f-8c29-4961-b8ab-76f625bbe252", "c3b0e13c-da7f-4ea0-a617-c902b189c482",
        "8fc20487-ceb9-46bc-a52d-08fef8be7916", "a2caa24c-12d1-446f-a578-d8d13984ddd0",
        "af0a901e-9db5-4fc1-a32c-216754274a61", "36092f24-40b3-46e5-be44-d3eafaca7994",
        "98d464d4-ab67-4873-9de4-fd26481de725", "4d69d3bf-afca-4883-98e4-aef6bd8780fc",
        "3cb3e655-7c18-46c5-b616-d14abba5e115", "0c51656e-d100-49ab-a7e1-21ca22d0040b"],
    8: ["c7eaa7ab-9949-4a1a-95ff-fc2db060f4a3", "464fbdaa-6002-40eb-96c6-a337c3f3bc59",
        "bc77b88a-f672-4c1d-8300-9478f7e48c2c", "94c7dc7a-730f-42d6-bf2c-8b8df9f4245d",
        "911b1c5c-fd92-4f64-9d67-4baec15c0417", "056d2de0-6526-4ceb-8425-721ce09e573c",
        "38d98be5-b9bd-45ca-8b20-a10991cd1919", "2f5422a4-fa22-4eac-912c-35d26ff14f3b",
        "adeade2e-7ea3-4838-bca5-fabec261686d", "0182d39c-de45-4715-8d27-683a57e9ada0",
        "52a3fce5-3e6c-4eb6-a71c-9b56612d64ae", "65b1ed6d-2398-424e-adf1-20bab67af74e",
        "38c3b1c6-c343-4cca-8fc3-87466fcbf5f3", "a7d98c42-a78d-44c4-b923-7cbc8e45f3b5",
        "49a202cc-13c1-4ea6-af5c-ee106a0931f1", "563d9156-f02b-45d3-97cd-17840d51a9bc",
        "cc4d9b30-508b-42cc-a216-b07a9d1e8c79", "276bc7fe-c458-4626-9608-150781b3a0c0",
        "35481ddc-6d58-41cc-ade9-640da2f57ba4", "58024c73-d5ff-49de-b3d4-4d293d52b589",
        "050f9a76-8b55-4e9b-b2b9-460c15d305db", "54c3cfb6-27f8-40dc-8716-2645682fc36c",
        "db70b5fe-c3e0-498d-9328-6788f6ae3142", "9eb38927-2932-44dc-944c-eba079bda53f",
        "26fdad4e-a466-46fd-8b05-669bde7ffa7f", "5679f9ae-70a0-45ed-a452-a1ac514e0393",
        "f70fae3b-29fb-4a5f-b430-63b351dfcb3d", "d1153b45-8144-4563-b5b4-1341048d6163",
        "62938c1d-80a4-4895-b1d8-601d41b7277b", "ff4435cf-b980-4bc9-93ad-0eff81f0c46b",
        "81e44746-8336-489c-be28-19d46477f630", "b7a7b202-3801-4d73-8e4e-b3aa3ef31657",
        "1ff13d03-a97f-452c-a5e4-a93c6ef85cc2", "c36a42a9-19f2-4b7f-99cc-536a2eb8ff23"],
}


# ============================================================
# 工具函数
# ============================================================
def encrypt_password(ts: int, password: str) -> str:
    hex_pwd = "".join(f"{ord(c):02x}" for c in password)
    raw = f"{ts}*{hex_pwd}"
    return base64.b64encode(raw.encode("ascii")).decode("ascii")


def parse_cookie_string(s: str) -> dict:
    out = {}
    for pair in (s or "").split(";"):
        pair = pair.strip()
        if not pair or "=" not in pair:
            continue
        k, v = pair.split("=", 1)
        out[k.strip()] = v.strip()
    return out


def load_cookie_from_file():
    """依次尝试 cookies.json / welearn_cookie.txt，返回 cookie 字符串"""
    # 1) cookies.json（Playwright 格式）
    if os.path.exists(COOKIE_JSON_FILE):
        try:
            with open(COOKIE_JSON_FILE, encoding="utf-8") as f:
                arr = json.load(f)
            parts = [f"{c['name']}={c['value']}" for c in arr
                     if ".sflep.com" in (c.get("domain") or "")]
            if parts:
                return "; ".join(parts), COOKIE_JSON_FILE
        except Exception:
            pass
    # 2) welearn_cookie.txt（一整行）
    if os.path.exists(COOKIE_TXT_FILE):
        try:
            with open(COOKIE_TXT_FILE, encoding="utf-8") as f:
                s = f.read().replace("\r", "").replace("\n", "").strip()
            if s:
                return s, COOKIE_TXT_FILE
        except Exception:
            pass
    return None, None


def load_scos_cache(cid: int) -> dict:
    try:
        with open(SCOS_CACHE_FILE, encoding="utf-8") as f:
            data = json.load(f)
        raw = data.get(str(cid))
        if not raw:
            return None
        # JSON 里 key 是字符串，转回 int
        return {int(k): v for k, v in raw.items()}
    except Exception:
        return None


def save_scos_cache(cid: int, unit_map: dict):
    try:
        if os.path.exists(SCOS_CACHE_FILE):
            with open(SCOS_CACHE_FILE, encoding="utf-8") as f:
                cache = json.load(f)
        else:
            cache = {}
        cache[str(cid)] = {str(k): v for k, v in unit_map.items()}
        with open(SCOS_CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(cache, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"[!] 写缓存失败: {e}")

# ============================================================
# 会话构造
# ============================================================
def make_session(cookie_string: str) -> requests.Session:
    s = requests.Session()
    s.headers.update({
        "User-Agent": UA,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    })
    if cookie_string:
        s.headers["Cookie"] = cookie_string
    return s


def check_alive(session: requests.Session, cid: int = 294) -> tuple:
    """返回 (bool, debug_text)"""
    old_xrw = session.headers.pop("X-Requested-With", None)
    try:
        r = session.get(
            f"{BASE}/student/course_info.aspx?cid={cid}&classid=788564",
            timeout=15, allow_redirects=True,
        )
        text = r.text or ""
        debug = f"status={r.status_code} len={len(text)} final={r.url[:80]}"
        low = text.lower()
        if "lisco_" in low or "authcourse.aspx" in low:
            return True, debug
        if any(k in low for k in ["prelogin", "signin-sflep", "loginredirect", "/idsvr/"]):
            return False, debug
        if "sso.sflep.com" in r.url.lower():
            return False, debug
        return r.status_code == 200, debug
    except Exception as e:
        return False, f"异常: {e}"
    finally:
        if old_xrw is not None:
            session.headers["X-Requested-With"] = old_xrw


def detect_user_context(session, cid: int = 294) -> dict:
    """自动探测 uid / classid / username"""
    result = {"uid": None, "classid": None, "username": None}
    for url in [
        f"{BASE}/student/course_info.aspx?cid={cid}&classid=788564",
        f"{BASE}/student/course_info.aspx?cid={cid}",
        f"{BASE}/student/StudyCourse.aspx?cid={cid}",
        f"{BASE}/student/index.aspx",
    ]:
        try:
            r = session.get(url, timeout=20, allow_redirects=True)
            html = r.text or ""
        except Exception:
            continue
        if not result["uid"]:
            for pat in [
                r"var\s+userid\s*=\s*(\d+)",
                r"var\s+uid\s*=\s*(\d+)",
                r"/Ajax/SCO\.aspx\?uid=(\d+)",
                r"[?&]uid=(\d+)",
                r"['\"]uid['\"]\s*[:=]\s*['\"]?(\d+)",
            ]:
                m = re.search(pat, html)
                if m:
                    result["uid"] = int(m.group(1))
                    break
        if not result["classid"]:
            for pat in [r"var\s+classid\s*=\s*(\d+)", r"[?&]classid=(\d+)"]:
                m = re.search(pat, html)
                if m:
                    result["classid"] = int(m.group(1))
                    break
        if not result["username"]:
            for pat in [r"var\s+username\s*=\s*['\"]([^'\"]+)['\"]"]:
                m = re.search(pat, html)
                if m:
                    result["username"] = unquote(m.group(1))
                    break
        if result["uid"] and result["classid"]:
            break
    return result if result["uid"] else None


# ============================================================
# Client（只挂时长，不动 interactions）
# ============================================================
class Client:
    def __init__(self, session, uid, cid, classid):
        self.s = session
        self.uid = uid
        self.cid = cid
        self.classid = classid
        self.ajax = f"{BASE}/Ajax/SCO.aspx?uid={uid}"

    def post(self, **params) -> dict:
        headers = {
            "X-Requested-With": "XMLHttpRequest",
            "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
            "Origin": BASE,
            "Referer": f"{BASE}/student/StudyCourse.aspx?cid={self.cid}",
            "Accept": "application/json, text/javascript, */*; q=0.01",
        }
        r = self.s.post(self.ajax, data=params, headers=headers, timeout=30)
        r.raise_for_status()
        try:
            return r.json()
        except Exception:
            return {"raw": r.text[:300]}

    def process_sco(self, scoid: str, *, wait: float, jitter: float = 0.0, log=None) -> tuple:
        if jitter > 0:
            actual_wait = wait + random.uniform(0, jitter)
        else:
            actual_wait = wait
        uid, cid, classid = self.uid, self.cid, self.classid
        # 风控
        r = self.post(action="isPausing", uid=uid, nocache=time.time())
        if r.get("isPausing"):
            raise RuntimeError(f"账号被锁定 {r.get('pausingMinute', '?')} 分钟")
        r = self.post(action="checkNoCaptcha", uid=uid, nocache=time.time())
        if r.get("status") == 0:
            raise RuntimeError("需要滑块验证")

        # SCO 地址
        r = self.post(action="scoAddr", cid=cid, scoid=scoid, nocache=time.time())
        if r.get("ret") != 0:
            raise RuntimeError(f"scoAddr 失败: {r}")

        # 历史 total_time
        hist_total = 0
        try:
            info = self.post(action="getscoinfo_v7", cid=cid, scoid=scoid,
                             uid=uid, nocache=time.time())
            raw = info.get("comment", "") or ""
            if raw:
                hist_total = int(json.loads(raw).get("cmi", {}).get("total_time", 0) or 0)
        except Exception:
            pass

        # 开始
        t0 = time.time()
        r = self.post(action="startsco160928", cid=cid, scoid=scoid,
                      uid=uid, classid=classid, tid=-1, nocache=time.time())
        if r.get("ret") != 0:
            raise RuntimeError(f"startsco 失败: {r}")
        timelimitsec = int(r.get("timelitsec", 0) or 0)

        # 只发心跳，不 setscoinfo
        while True:
            now = time.time()
            if now - t0 >= actual_wait:
                break
            time.sleep(max(0.1, min(60.0, actual_wait - (now - t0))))
            sec = int(time.time() - t0)
            if sec <= 0:
                continue
            try:
                self.post(action="keepsco_with_getticket_with_updatecmitime",
                          uid=uid, cid=cid, scoid=scoid,
                          session_time=sec, total_time=hist_total + sec,
                          timelimitsec=timelimitsec, endcaltime="false",
                          nocache=time.time())
            except Exception:
                pass

        r = self.post(action="savescoinfo160928", cid=cid, scoid=scoid, uid=uid,
                      progress=1, crate="", status="unknown",
                      cstatus="completed", trycount=0, endcaltime="false",
                      nocache=time.time())
        return scoid, int(r.get("seconds", 0) or 0)
    
    def _extract_scos_from_block(self, html: str) -> list:
        """
        从一段 HTML 里提取叶子 SCO（不含 section 容器节点）。
        判定依据：
          · 容器节点：<span class="list_brunch"> 或 list_brunch_2 —— 有子目录
          · 叶子节点：没有 list_brunch，直接可学
        返回纯 uuid（不带 ITEM- 前缀）。
        """
        # 按 <li id="liSCO_ITEM- 切分，逐个分析
        parts = re.split(r'(?=<li\s+id="liSCO_ITEM-)', html)
        leaves, all_ids = [], []
        seen_l, seen_a = set(), set()

        for part in parts:
            m = re.match(r'<li\s+id="liSCO_ITEM-([0-9a-fA-F\-]+)"', part)
            if not m:
                continue
            sco_id = m.group(1)

            # 只取到这个 <li> 的闭合
            end = part.find('</li>')
            li_content = part[:end] if end >= 0 else part[:800]

            # 全部记录（兜底用）
            if sco_id not in seen_a:
                seen_a.add(sco_id)
                all_ids.append(sco_id)

            # 容器：含 list_brunch / list_brunch_2 的跳过
            if 'list_brunch' in li_content:
                continue

            # 叶子
            if sco_id not in seen_l:
                seen_l.add(sco_id)
                leaves.append(sco_id)

        # 优先返回叶子；如果某课程所有节点都是 section 格式，兜底返回全部
        return leaves if leaves else all_ids

    def fetch_course_scos(self, log=None) -> dict:
        """
        抓 SCO 结构，返回 {unit_no: [scoid, ...]}。
        unit_no=0 表示未归属 Unit 的（课程说明等）。
        优先 StudyCourse.aspx（结构清晰），其次 course_info.aspx。
        """
        def _log(msg):
            if log:
                log(msg)
            else:
                print(msg)

        urls = [
            # StudyCourse.aspx 结构最清晰，<span class="v_1">Unit N</span> + <li id="liSCO_ITEM-xxx">
            f"{BASE}/student/StudyCourse.aspx?cid={self.cid}&classid={self.classid}",
            # course_info.aspx 兜底（Unit 标题在 <a> 文本里）
            f"{BASE}/student/course_info.aspx?cid={self.cid}&classid={self.classid}",
            f"{BASE}/student/course_info.aspx?cid={self.cid}",
        ]

        for url in urls:
            try:
                r = self.s.get(url, timeout=30, allow_redirects=True)
                html = r.text or ""
            except Exception as e:
                _log(f"[!] 抓 {url} 失败: {e}")
                continue

            total_li = len(re.findall(r'liSCO_', html))
            _log(f"[.] {url.split('?')[0].split('/')[-1]}  "
                 f"len={len(html)}  liSCO_×{total_li}")
            if total_li == 0:
                continue

            # 正则一：StudyCourse.aspx 里的 <span class="v_1">Unit N ...</span>
            unit_markers = list(re.finditer(
                r'<span\s+class="v_1">\s*Unit\s+(\d+)[^<]*</span>',
                html,
            ))

            # 正则二：course_info.aspx 里的 <a ...>Unit N ...</a>
            if not unit_markers:
                unit_markers = list(re.finditer(
                    r'>\s*Unit\s+(\d+)\s+[^<]+',
                    html,
                ))
                _log(f"[.] 使用 course_info 模式匹配 Unit，找到 {len(unit_markers)} 个标记")

            if not unit_markers:
                # 实在找不到 Unit，把所有 SCO 归到 unit 0
                all_ids = self._extract_scos_from_block(html)
                if all_ids:
                    _log(f"[!] 未识别到 Unit 标记，全部归到 unit 0（{len(all_ids)} 个）")
                    return {0: all_ids}
                continue

            _log(f"[.] 找到 {len(unit_markers)} 个 Unit 标记")

            result = {}
            # 第一个 Unit 之前的内容（课程说明等）归到 0
            head = html[:unit_markers[0].start()]
            head_ids = self._extract_scos_from_block(head)
            if head_ids:
                result[0] = head_ids

            for idx, m in enumerate(unit_markers):
                unit_no = int(m.group(1))
                start = m.end()
                end = unit_markers[idx + 1].start() if idx + 1 < len(unit_markers) else len(html)
                block = html[start:end]
                ids = self._extract_scos_from_block(block)
                if ids:
                    result[unit_no] = ids
                    _log(f"    Unit {unit_no}: {len(ids)} 个 SCO")

            if result:
                return result

        return {}


# ============================================================
# Playwright 自动登录
# ============================================================
def playwright_login(username: str, password: str, log) -> bool:
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        log("[!] 未安装 playwright，运行：pip install playwright && playwright install chromium")
        return False

    log("[*] 启动 Chromium 浏览器 ...")
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=False, channel="msedge")
            ctx = browser.new_context()
            page = ctx.new_page()
            log("[*] 打开登录页 ...")
            page.goto(
                f"{BASE}/user/prelogin.aspx?loginret=http://welearn.sflep.com/user/loginredirect.aspx",
                wait_until="domcontentloaded", timeout=60000,
            )
            log("[*] 等待登录表单 ...")
            page.wait_for_selector("#username", timeout=60000)
            page.fill("#username", username)
            page.fill("#password", password)
            log("[*] 提交 ...")
            page.click("#login")
            log("[*] 等待跳转（若出现滑块请手动完成，最长 3 分钟）...")
            page.wait_for_url("**/student/**", timeout=180000)
            log("[+] 登录成功，保存 cookies ...")
            cookies = ctx.cookies()
            with open(COOKIE_JSON_FILE, "w", encoding="utf-8") as f:
                json.dump(cookies, f, ensure_ascii=False, indent=2)
            browser.close()
            log(f"[+] 已保存到 {COOKIE_JSON_FILE}")
            return True
    except Exception as e:
        log(f"[!] 浏览器登录失败: {e}")
        return False


# ============================================================
# GUI
# ============================================================
class App:
    def __init__(self, root):
        self.root = root
        root.title("WELearn 挂时长工具")
        root.geometry("880x680")

        self.log_queue = queue.Queue()
        self.stop_flag = threading.Event()
        self.worker_thread = None
        self.session = None
        self.uid = None
        self.classid = 114514
        self.cid = 294
        self.course_scos = {}
        self.scos_source = ""

        self._build_ui()
        self._poll_log()

    # ---------------- UI ----------------
    def _build_ui(self):
        # ---- 顶部：登录区 ----
        login_frm = ttk.LabelFrame(self.root, text="① 登录", padding=8)
        login_frm.pack(fill="x", padx=8, pady=4)

        r1 = ttk.Frame(login_frm); r1.pack(fill="x", pady=2)
        ttk.Label(r1, text="账号:").pack(side="left")
        self.entry_user = ttk.Entry(r1, width=20)
        self.entry_user.pack(side="left", padx=4)
        ttk.Label(r1, text="密码:").pack(side="left")
        self.entry_pwd = ttk.Entry(r1, width=20, show="*")
        self.entry_pwd.pack(side="left", padx=4)
        self.btn_pwlogin = ttk.Button(r1, text="浏览器登录", command=self.on_playwright_login)
        self.btn_pwlogin.pack(side="left", padx=4)
        self.btn_use_cookie = ttk.Button(r1, text="读取本地 Cookie", command=self.on_load_cookie)
        self.btn_use_cookie.pack(side="left", padx=4)

        r2 = ttk.Frame(login_frm); r2.pack(fill="x", pady=2)
        ttk.Label(r2, text="Cookie:").pack(side="left")
        self.entry_cookie = ttk.Entry(r2)
        self.entry_cookie.pack(side="left", fill="x", expand=True, padx=4)
        self.btn_check = ttk.Button(r2, text="验证登录", command=self.on_check_login)
        self.btn_check.pack(side="left")

        # ---- 参数区 ----
        param_frm = ttk.LabelFrame(self.root, text="② 参数", padding=8)
        param_frm.pack(fill="x", padx=8, pady=4)

        r3 = ttk.Frame(param_frm); r3.pack(fill="x", pady=2)
        ttk.Label(r3, text="Unit:").pack(side="left")
        self.combo_unit = ttk.Combobox(r3, width=8, state="readonly",
                                       values=["全部"] + [f"Unit {i}" for i in range(1, 9)])
        self.combo_unit.current(0)
        self.combo_unit.pack(side="left", padx=4)

        ttk.Label(r3, text="每 SCO 停留(秒):").pack(side="left", padx=(12, 0))
        self.entry_wait = ttk.Entry(r3, width=6)
        self.entry_wait.insert(0, "90")
        self.entry_wait.pack(side="left", padx=4)

        ttk.Label(r3, text="抖动(秒):").pack(side="left", padx=(12, 0))
        self.entry_jitter = ttk.Spinbox(r3, from_=0, to=120, width=5, increment=1)
        self.entry_jitter.set(5)
        self.entry_jitter.pack(side="left", padx=4)

        ttk.Label(r3, text="并发:").pack(side="left", padx=(12, 0))
        self.entry_workers = ttk.Entry(r3, width=4)
        self.entry_workers.insert(0, "2")
        self.entry_workers.pack(side="left", padx=4)

        ttk.Label(r3, text="课程 ID:").pack(side="left", padx=(12, 0))
        self.entry_cid = ttk.Entry(r3, width=6)
        self.entry_cid.insert(0, "294")
        self.entry_cid.pack(side="left", padx=4)

        ttk.Label(r3, text="班级 ID:").pack(side="left", padx=(12, 0))
        self.entry_classid = ttk.Entry(r3, width=8)
        self.entry_classid.insert(0, "788564")
        self.entry_classid.pack(side="left", padx=4)

        r4 = ttk.Frame(param_frm); r4.pack(fill="x", pady=2)
        ttk.Label(r4, text="用户 ID:").pack(side="left")
        self.entry_uid = ttk.Entry(r4, width=10)
        self.entry_uid.pack(side="left", padx=4)
        ttk.Label(r4, text="（留空自动探测）", foreground="gray").pack(side="left")
        self.btn_probe = ttk.Button(r4, text="探测 uid", command=self.on_probe_uid)
        self.btn_probe.pack(side="left", padx=8)

        # ---- 按钮区 ----
        btn_frm = ttk.Frame(self.root, padding=4)
        btn_frm.pack(fill="x", padx=8, pady=4)
        self.btn_start = ttk.Button(btn_frm, text="▶ 开始挂机", command=self.on_start)
        self.btn_start.pack(side="left", padx=4)
        self.btn_dryrun = ttk.Button(btn_frm, text="列出 SCO", command=self.on_dry_run)
        self.btn_dryrun.pack(side="left", padx=4)
        self.btn_refetch = ttk.Button(btn_frm, text="重抓 SCO", command=self.on_refetch_scos)
        self.btn_refetch.pack(side="left", padx=4)
        self.btn_stop = ttk.Button(btn_frm, text="⏹ 停止", command=self.on_stop, state="disabled")
        self.btn_stop.pack(side="left", padx=4)

        # ---- 进度 ----
        prog_frm = ttk.Frame(self.root, padding=4)
        prog_frm.pack(fill="x", padx=8)
        self.progress = ttk.Progressbar(prog_frm, mode="determinate")
        self.progress.pack(fill="x")
        self.lbl_status = ttk.Label(prog_frm, text="就绪", foreground="#666")
        self.lbl_status.pack(anchor="w", pady=2)

        # ---- 日志 ----
        log_frm = ttk.LabelFrame(self.root, text="③ 日志", padding=4)
        log_frm.pack(fill="both", expand=True, padx=8, pady=4)
        self.txt_log = scrolledtext.ScrolledText(log_frm, height=18,
                                                 font=("Consolas", 9))
        self.txt_log.pack(fill="both", expand=True)

    # ---------------- 日志 ----------------
    def log(self, msg):
        self.log_queue.put(msg)

    def _poll_log(self):
        try:
            while True:
                msg = self.log_queue.get_nowait()
                self.txt_log.insert("end", str(msg) + "\n")
                self.txt_log.see("end")
        except queue.Empty:
            pass
        self.root.after(100, self._poll_log)

    def _set_status(self, s):
        self.lbl_status.config(text=s)

    # ---------------- 登录 ----------------
    def on_playwright_login(self):
        u = self.entry_user.get().strip()
        p = self.entry_pwd.get().strip()
        if not u or not p:
            messagebox.showwarning("提示", "请填写账号和密码")
            return
        def run():
            ok = playwright_login(u, p, self.log)
            if ok:
                cookie, src = load_cookie_from_file()
                if cookie:
                    self.root.after(0, lambda: self.entry_cookie.delete(0, "end"))
                    self.root.after(0, lambda: self.entry_cookie.insert(0, cookie))
                    self.log(f"[+] 已自动填入 {src} 的 cookie")
                    self.root.after(0, self.on_check_login)
        threading.Thread(target=run, daemon=True).start()

    def on_load_cookie(self):
        cookie, src = load_cookie_from_file()
        if not cookie:
            messagebox.showwarning("提示", f"未找到 {COOKIE_JSON_FILE} 或 {COOKIE_TXT_FILE}")
            return
        self.entry_cookie.delete(0, "end")
        self.entry_cookie.insert(0, cookie)
        self.log(f"[+] 已加载 {src}（{len(cookie)} 字符）")

    def _update_unit_combo(self, unit_map: dict):
        """按抓到的 Unit 列表更新下拉框"""
        units = sorted(k for k in unit_map if k > 0)
        values = ["全部"] + [f"Unit {u}" for u in units]
        self.combo_unit.config(values=values)
        self.combo_unit.current(0)

    def on_check_login(self):
        cookie = self.entry_cookie.get().strip()
        if not cookie:
            messagebox.showwarning("提示", "cookie 为空")
            return
        cid = int(self.entry_cid.get().strip() or 294)
        def run():
            self.log("[*] 验证登录态 ...")
            s = make_session(cookie)
            ok, dbg = check_alive(s, cid)
            self.log(f"    [debug] {dbg}")
            if not ok:
                self.log("[!] 登录无效，请重新获取 cookie")
                return

            self.log("[+] 登录状态有效")
            self.session = s

            # 步骤 1：先探测 uid / classid
            self.log("[*] 探测用户信息 ...")
            ctx = detect_user_context(s, cid)
            if ctx:
                self.uid = ctx["uid"]
                if ctx.get("classid"):
                    self.classid = ctx["classid"]
                self.log(f"[+] uid={self.uid}  classid={self.classid}  "
                         f"username={ctx.get('username') or '未知'}")
                self.root.after(0, lambda: self.entry_uid.delete(0, "end"))
                self.root.after(0, lambda: self.entry_uid.insert(0, str(self.uid)))
                self.root.after(0, lambda: self.entry_classid.delete(0, "end"))
                self.root.after(0, lambda: self.entry_classid.insert(0, str(self.classid)))
            else:
                self.log("[!] 未探测到 uid，SCO 抓取可能受影响")

            # 步骤 2：再抓 SCO 结构
            self.log("[*] 抓取课程 SCO 结构 ...")
            cli = Client(s, self.uid or 0, cid, self.classid)
            unit_map = cli.fetch_course_scos()

            if unit_map:
                self.course_scos = unit_map
                self.scos_source = "web"
                save_scos_cache(cid, unit_map)
                total = sum(len(v) for v in unit_map.values())
                units = sorted(k for k in unit_map if k > 0)
                self.log(f"[+] 抓取成功：{len(unit_map)} 组，共 {total} 个 SCO")
                self.log(f"    Units: {units}")
                self.root.after(0, lambda: self._update_unit_combo(unit_map))
            else:
                self.log("[!] 网页抓取失败，尝试读缓存 ...")
                cached = load_scos_cache(cid)
                if cached:
                    self.course_scos = cached
                    self.scos_source = "cache"
                    total = sum(len(v) for v in cached.values())
                    self.log(f"[+] 从缓存加载：{total} 个 SCO")
                    self.root.after(0, lambda: self._update_unit_combo(cached))
                else:
                    self.log("[!] 无缓存，将退回内置 BOOKINFO_UNITS")

        threading.Thread(target=run, daemon=True).start()

    def on_probe_uid(self):
        if not self.session:
            messagebox.showwarning("提示", "请先验证登录")
            return
        cid = int(self.entry_cid.get().strip() or 294)
        def run():
            ctx = detect_user_context(self.session, cid)
            if ctx:
                self.uid = ctx["uid"]
                if ctx.get("classid"):
                    self.classid = ctx["classid"]
                self.log(f"[+] uid={self.uid}  classid={self.classid}")
                self.root.after(0, lambda: self.entry_uid.delete(0, "end"))
                self.root.after(0, lambda: self.entry_uid.insert(0, str(self.uid)))
                self.root.after(0, lambda: self.entry_classid.delete(0, "end"))
                self.root.after(0, lambda: self.entry_classid.insert(0, str(self.classid)))
            else:
                self.log("[!] 探测失败")
        threading.Thread(target=run, daemon=True).start()

    # ---------------- 刷课 ----------------
    def _resolve_scos(self):
        unit_sel = self.combo_unit.get()

        # 优先用动态抓到的
        if self.course_scos:
            if unit_sel.startswith("Unit"):
                n = int(unit_sel.split()[1])
                return [f"ITEM-{i}" for i in self.course_scos.get(n, [])]
            else:
                # 全部：跳过 unit 0（课程说明），除非只有一个 unit
                out = []
                for u in sorted(self.course_scos.keys()):
                    if u == 0:
                        continue
                    out.extend(f"ITEM-{i}" for i in self.course_scos[u])
                # 如果没有任何 unit>0，就把 0 里的也放进来
                if not out:
                    out = [f"ITEM-{i}" for i in self.course_scos.get(0, [])]
                return out

        # 退化到内置
        if unit_sel.startswith("Unit"):
            n = int(unit_sel.split()[1])
            ids = BOOKINFO_UNITS.get(n, [])
            return [f"ITEM-{i}" for i in ids]
        out = []
        for u in sorted(BOOKINFO_UNITS.keys()):
            out.extend(f"ITEM-{i}" for i in BOOKINFO_UNITS[u])
        return out

    def on_refetch_scos(self):
        if not self.session:
            messagebox.showwarning("提示", "请先验证登录")
            return
        cid = int(self.entry_cid.get().strip() or 294)
        classid = int(self.entry_classid.get().strip() or 788564)
        def run():
            self.log(f"[*] 重新抓取 cid={cid} 的 SCO 结构 ...")
            cli = Client(self.session, self.uid or 0, cid, classid)
            unit_map = cli.fetch_course_scos(log=self.log)   # ← 传 log
            if unit_map:
                self.course_scos = unit_map
                self.scos_source = "web"
                save_scos_cache(cid, unit_map)
                total = sum(len(v) for v in unit_map.values())
                self.log(f"[+] 抓取成功：{total} 个 SCO，"
                         f"Units={sorted(k for k in unit_map if k > 0)}")
                self.root.after(0, lambda: self._update_unit_combo(unit_map))
            else:
                self.log("[!] 抓取失败，保持原样")
        threading.Thread(target=run, daemon=True).start()

    def on_dry_run(self):
        scos = self._resolve_scos()
        self.log(f"[*] 共 {len(scos)} 个 SCO")
        for s in scos:
            self.log("    " + s)

    def on_start(self):
        if not self.session:
            messagebox.showwarning("提示", "请先验证登录")
            return
        uid = self.entry_uid.get().strip()
        if not uid:
            self.log("[*] uid 为空，自动探测 ...")
            ctx = detect_user_context(self.session, int(self.entry_cid.get().strip() or 294))
            if not ctx:
                messagebox.showerror("错误", "无法探测 uid，请手动填写")
                return
            self.uid = ctx["uid"]
            self.entry_uid.insert(0, str(self.uid))
        else:
            self.uid = int(uid)

        self.classid = int(self.entry_classid.get().strip() or 788564)
        cid = int(self.entry_cid.get().strip() or 294)
        wait = float(self.entry_wait.get().strip() or 90)
        jitter = float(self.entry_jitter.get().strip() or 0)
        workers = int(self.entry_workers.get().strip() or 2)
        cookie = self.entry_cookie.get().strip()

        scos = self._resolve_scos()
        if not scos:
            messagebox.showwarning("提示", "SCO 列表为空")
            return

        self.stop_flag.clear()
        self.btn_start.config(state="disabled")
        self.btn_stop.config(state="normal")
        self.progress.config(maximum=len(scos), value=0)
        self._set_status(f"开始挂机：{len(scos)} 个 SCO")

        self.worker_thread = threading.Thread(
            target=self._run_workers,
            args=(scos, cid, self.classid, wait, jitter, workers, cookie),
            daemon=True,
        )
        self.worker_thread.start()

    def _run_workers(self, scos, cid, classid, wait, jitter, workers, cookie):
        log = self.log
        log(f"[*] 共 {len(scos)} 个 SCO，wait={wait}s，workers={workers}")
        lock = threading.Lock()
        state = {"done": 0, "sec": 0, "ok": 0, "fail": 0}
        t0 = time.time()

        def worker(idx_sco):
            idx, scoid = idx_sco
            if self.stop_flag.is_set():
                return None
            s = make_session(cookie)
            c = Client(s, self.uid, cid, classid)
            try:
                _, sec = c.process_sco(scoid, wait=wait, log=log)
                with lock:
                    state["done"] += 1
                    state["sec"] += sec
                    state["ok"] += 1
                    log(f"[{state['done']:>3}/{len(scos)}] ✅ {scoid[:28]}…  +{sec}s")
                    self.root.after(0, lambda: self.progress.config(value=state["done"]))
                return True
            except Exception as e:
                with lock:
                    state["done"] += 1
                    state["fail"] += 1
                    log(f"[{state['done']:>3}/{len(scos)}] ❌ {scoid[:28]}…  {e}")
                    self.root.after(0, lambda: self.progress.config(value=state["done"]))
                return False

        with ThreadPoolExecutor(max_workers=workers) as ex:
            list(ex.map(worker, enumerate(scos)))

        dt = time.time() - t0
        log(f"\n===== 完成 =====")
        log(f"成功 {state['ok']} / 失败 {state['fail']} / 总计 {len(scos)}")
        log(f"服务器累计 +{state['sec']}s（{state['sec']/60:.1f} 分钟）")
        log(f"实际耗时 {dt:.1f}s")
        self.root.after(0, lambda: self.btn_start.config(state="normal"))
        self.root.after(0, lambda: self.btn_stop.config(state="disabled"))
        self.root.after(0, lambda: self._set_status("完成"))

    def on_stop(self):
        self.stop_flag.set()
        self.log("[!] 已请求停止，等待当前 SCO 结束 ...")
        self._set_status("停止中...")


# ============================================================
# main
# ============================================================
def main():
    root = tk.Tk()
    try:
        ttk.Style().theme_use("vista" if sys.platform == "win32" else "clam")
    except Exception:
        pass
    App(root)
    root.mainloop()


if __name__ == "__main__":
    main()