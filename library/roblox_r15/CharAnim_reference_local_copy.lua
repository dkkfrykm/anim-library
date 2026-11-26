--!nonstrict
-- Client.CharAnim: procedural character animation for powers. Clips are authored in Blender
-- (soulbound/anim, baked + exported into the Clips_* children) and played by writing Motor6D.Transform
-- in Stepped, layered over the default Animate tracks (blend in, override, blend back out).
-- Timing: a clip's first IMPACT marker is time-stretched to land at `impactAt` seconds; multi-hit moves
-- loop an 18-frame (0.3 s) cycle so every server hit lands on an impact frame.
-- R15 only; R6 characters are skipped (no attack animation, nothing breaks).
local Players = game:GetService("Players")
local RunService = game:GetService("RunService")
local TweenService = game:GetService("TweenService")
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local Powers = require(ReplicatedStorage.Shared.Config.Powers)

local CharAnim = {}

------------------------------------------------------------------------ clip decoding
local JOINT = { Rt = "Root", W = "Waist", N = "Neck", RS = "RightShoulder", RE = "RightElbow", RW = "RightWrist",
	LS = "LeftShoulder", LE = "LeftElbow", LW = "LeftWrist", RH = "RightHip", RK = "RightKnee", RA = "RightAnkle",
	LH = "LeftHip", LK = "LeftKnee", LA = "LeftAnkle" }
local PART = { Root = "LowerTorso", Waist = "UpperTorso", Neck = "Head", RightShoulder = "RightUpperArm",
	RightElbow = "RightLowerArm", RightWrist = "RightHand", LeftShoulder = "LeftUpperArm", LeftElbow = "LeftLowerArm",
	LeftWrist = "LeftHand", RightHip = "RightUpperLeg", RightKnee = "RightLowerLeg", RightAnkle = "RightFoot",
	LeftHip = "LeftUpperLeg", LeftKnee = "LeftLowerLeg", LeftAnkle = "LeftFoot" }
local LEGS = { RightHip = true, RightKnee = true, RightAnkle = true, LeftHip = true, LeftKnee = true, LeftAnkle = true }

local function idx(s, i)
	local b = string.byte(s, i)
	return b - 35 - (b > 93 and 1 or 0)
end

local function decode(raw)
	local c = { n = raw.n, w = raw.w, i = raw.i, r = raw.r, la = raw.la, lb = raw.lb, j = {} }
	local rad = math.rad
	for short, s in raw do
		local name = JOINT[short]
		if name and type(s) == "string" then
			local fs, cfs, f = {}, {}, 0
			for k = 1, #s, 4 do
				f += idx(s, k)
				fs[#fs + 1] = f
				cfs[#cfs + 1] = CFrame.Angles(rad(idx(s, k + 1) * 4 - 180), rad(idx(s, k + 2) * 4 - 180), rad(idx(s, k + 3) * 4 - 180))
			end
			c.j[name] = { f = fs, v = cfs }
		end
	end
	if type(raw.p) == "string" then
		local s, fs, vs, f = raw.p, {}, {}, 0
		local function e2(k)
			return (idx(s, k) * 91 + idx(s, k + 1) - 4000) / 100
		end
		for k = 1, #s, 7 do
			f += idx(s, k)
			fs[#fs + 1] = f
			vs[#vs + 1] = Vector3.new(e2(k + 1), e2(k + 3), e2(k + 5))
		end
		c.p = { f = fs, v = vs }
	end
	return c
end

local CLIPS = {}
for _, m in script:GetChildren() do
	if m:IsA("ModuleScript") and m.Name:sub(1, 6) == "Clips_" then
		local ok, t = pcall(require, m)
		if ok and type(t) == "table" then
			for name, raw in t do
				CLIPS[name] = decode(raw)
			end
		else
			warn("[CharAnim] clip module failed: " .. m.Name)
		end
	end
end
CharAnim.Clips = CLIPS

local function sample(track, f, lerp)
	local fs, vs = track.f, track.v
	local n = #fs
	if f <= fs[1] then
		return vs[1]
	elseif f >= fs[n] then
		return vs[n]
	end
	local lo, hi = 1, n
	while hi - lo > 1 do
		local mid = (lo + hi) // 2
		if fs[mid] <= f then
			lo = mid
		else
			hi = mid
		end
	end
	local a = (f - fs[lo]) / (fs[hi] - fs[lo])
	return lerp(vs[lo], vs[hi], a)
end
local function lerpCF(a, b, t)
	return a:Lerp(b, t)
end
local function lerpV(a, b, t)
	return a:Lerp(b, t)
end

------------------------------------------------------------------------ style mapping (all 38 powers)
-- style, m1 set, weapon, amp (pose amplitude), spd (recovery speed)
local S = {}
local function set(style, ids, extra)
	for _, id in ids do
		S[id] = table.clone(extra or {})
		S[id].style = style
	end
end
set("Fighter", { "brawler", "boxer", "karate", "windfist", "speedster", "flamefist", "frosttouch", "thunderfist", "dragonfist", "phantomstep" })
set("Fighter", { "kicker", "acrobat" }, { m1 = "Kick" })
set("Fighter", { "limitbreaker" }, { amp = 0.85 }) -- "casual" — smaller, lazier poses until the ultimate
set("Blade", { "bladedancer" }, { weapon = "TwinSpirit" })
set("Blade", { "sunblade" }, { weapon = "Sunblade", amp = 1.05 })
set("Blade", { "soulblade" }, { weapon = "SpectralKatana" })
set("Blade", { "demonhunter" }, { weapon = "DemonKatana", spd = 1.1 })
set("Blade", { "soulrequiem" }, { weapon = "PetalKatana" })
set("Mystic", { "chakra", "psychic", "chakramaster", "voidsovereign", "starbornascension", "astraloverlord", "infinityarchitect",
	"supernovagod", "absoluteinfinity", "divinesaiyan" })
set("Beast", { "beastform", "dragonshift" })
set("Spirit", { "stando" }, { m1 = "Fighter" })
set("Spirit", { "eclipsemonarch", "eclipseblacksun" }, { m1 = "Blade", weapon = "ShadowDaggers" })
set("Titan", { "ironbody", "titanstrength", "unitedmight", "elasticemperor", "overdrive" })
CharAnim.Styles = S

local RANK = { Mythical = true, Celestial = true, Secret = true }

function CharAnim.StyleOf(pid)
	return S[pid] or { style = "Fighter" }
end

-- clip name for a move (with fallbacks)
function CharAnim.ClipName(pid, slot, kind, combo)
	local st = CharAnim.StyleOf(pid)
	local style = st.style
	local name
	if slot == "M1" or kind == "Punch" then
		local set = st.m1 or (style == "Spirit" and "Fighter" or style)
		name = ("%s_M1_%d"):format(set, ((combo or 1) - 1) % 4 + 1)
	elseif slot == "G" then
		if style == "Blade" then
			name = "Blade_Ult"
		elseif kind == "Dash" then
			name = style .. "_Dash"
		elseif kind == "Burst" then
			name = (style == "Mystic" or style == "Spirit") and "Ult_Nuke" or "Ult_Leap"
		else
			name = (style == "Fighter" or style == "Titan") and (style .. "_Blast") or "Ult_Beam"
		end
	else
		name = style .. "_" .. tostring(kind)
	end
	if not CLIPS[name] then
		name = "Fighter_" .. tostring(kind == "Punch" and "M1_1" or kind)
	end
	return CLIPS[name] and name or nil
end

------------------------------------------------------------------------ weapons (Part-built, client-side)
local function wp(model, size, cf, color, mat, tr, shape)
	local p = Instance.new("Part")
	p.Size = size
	p.CFrame = cf
	p.Color = color
	p.Material = mat or Enum.Material.SmoothPlastic
	p.Transparency = tr or 0
	if shape then
		p.Shape = shape
	end
	p.CanCollide, p.CanQuery, p.CanTouch, p.Massless, p.Anchored = false, false, false, true, false
	p.CastShadow = false
	p:SetAttribute("BaseTr", p.Transparency)
	p.Parent = model
	return p
end
local function wedge(model, size, cf, color, mat, tr)
	local p = Instance.new("WedgePart")
	p.Size, p.CFrame, p.Color, p.Material, p.Transparency = size, cf, color, mat or Enum.Material.SmoothPlastic, tr or 0
	p.CanCollide, p.CanQuery, p.CanTouch, p.Massless, p.Anchored, p.CastShadow = false, false, false, true, false, false
	p:SetAttribute("BaseTr", p.Transparency)
	p.Parent = model
	return p
end
-- builds a blade along -Z from the grip (origin). opts: len, wid, col (blade), glow (edge), hilt, curve, ghost
local function blade(opts)
	local m = Instance.new("Model")
	m.Name = "Weapon"
	local L, Wd = opts.len or 3.6, opts.wid or 0.34
	local hilt = opts.hilt or Color3.fromRGB(40, 30, 45)
	local grip = wp(m, Vector3.new(0.22, 0.22, 0.9), CFrame.new(0, 0, 0.25), hilt)
	grip.Name = "Grip"
	wp(m, Vector3.new(0.28, 0.28, 0.16), CFrame.new(0, 0, 0.75), opts.glow, Enum.Material.Neon)
	wp(m, Vector3.new(opts.guard or 0.8, 0.14, 0.2), CFrame.new(0, 0, -0.25), opts.guardCol or opts.glow, Enum.Material.Neon)
	local tr = opts.ghost and 0.35 or 0
	local segs = opts.curve and 3 or 1
	local cf = CFrame.new(0, 0, -0.35)
	local segL = L / segs
	for i = 1, segs do
		local mid = cf * CFrame.new(0, 0, -segL / 2)
		wp(m, Vector3.new(0.1, Wd, segL), mid, opts.col, opts.mat or Enum.Material.Metal, tr)
		wp(m, Vector3.new(0.12, 0.07, segL), mid * CFrame.new(0, Wd / 2, 0), opts.glow, Enum.Material.Neon, tr * 0.5)
		cf = cf * CFrame.new(0, 0, -segL) * CFrame.Angles(opts.curve and math.rad(opts.curve) or 0, 0, 0)
	end
	wedge(m, Vector3.new(0.1, Wd, 0.6), cf * CFrame.new(0, 0, -0.3) * CFrame.Angles(0, math.pi, 0), opts.glow, Enum.Material.Neon, tr * 0.5)
	m.PrimaryPart = grip
	return m
end
local WEAPONS = {
	TwinSpirit = { twin = true, make = function(c, c2) return blade({ len = 2.8, wid = 0.4, col = c2, glow = c, mat = Enum.Material.Glass, ghost = true, curve = 8 }) end },
	Sunblade = { make = function(c, c2) return blade({ len = 4.2, wid = 0.5, col = Color3.fromRGB(255, 230, 150), glow = c, guard = 1.3, guardCol = Color3.fromRGB(255, 200, 60), mat = Enum.Material.Neon }) end },
	SpectralKatana = { make = function(c, c2) return blade({ len = 4.0, wid = 0.26, col = c2, glow = c, mat = Enum.Material.ForceField, ghost = true, curve = 5, guard = 0.5 }) end },
	DemonKatana = { make = function(c, c2) return blade({ len = 3.9, wid = 0.26, col = Color3.fromRGB(30, 20, 26), glow = c, curve = 5, guard = 0.5, guardCol = c2 }) end },
	PetalKatana = { make = function(c, c2) return blade({ len = 3.8, wid = 0.26, col = Color3.fromRGB(255, 220, 235), glow = c, curve = 6, guard = 0.5 }) end },
	ShadowDaggers = { twin = true, make = function(c, c2) return blade({ len = 1.8, wid = 0.36, col = Color3.fromRGB(25, 20, 40), glow = c, guard = 0.5 }) end },
}
CharAnim.Weapons = WEAPONS

local held = {} -- [char] = { models = {}, until = t }
local function setTr(model, a)
	for _, p in model:GetDescendants() do
		if p:IsA("BasePart") then
			local b = p:GetAttribute("BaseTr") or 0
			p.Transparency = b + (1 - b) * a
		end
	end
end
local function flash(hand, color)
	local s = Instance.new("Part")
	s.Shape = Enum.PartType.Ball
	s.Material = Enum.Material.Neon
	s.Color = color
	s.Size = Vector3.new(0.4, 0.4, 0.4)
	s.CanCollide, s.CanQuery, s.CanTouch, s.Anchored, s.CastShadow = false, false, false, true, false
	s.CFrame = hand.CFrame
	s.Parent = workspace
	TweenService:Create(s, TweenInfo.new(0.22, Enum.EasingStyle.Quad, Enum.EasingDirection.Out), { Size = Vector3.new(2.6, 2.6, 2.6), Transparency = 1 }):Play()
	task.delay(0.25, s.Destroy, s)
end
local function summon(char, pid, holdFor)
	local st = S[pid]
	local spec = st and st.weapon and WEAPONS[st.weapon]
	if not spec then
		return
	end
	local h = held[char]
	if h then
		h.until = math.max(h.until, os.clock() + holdFor)
		return
	end
	local def = Powers.ById[pid]
	local c = def and def.Palette.Glow or Color3.new(1, 1, 1)
	local c2 = def and def.Palette.Primary or c
	h = { models = {}, until = os.clock() + holdFor }
	held[char] = h
	for _, side in (spec.twin and { "Right", "Left" } or { "Right" }) do
		local hand = char:FindFirstChild(side .. "Hand")
		if hand then
			local m = spec.make(c, c2)
			local wld = Instance.new("Weld")
			wld.Part0 = hand
			wld.Part1 = m.PrimaryPart
			wld.C0 = CFrame.new(0, -0.18, 0)
			wld.Parent = m.PrimaryPart
			for _, p in m:GetDescendants() do
				if p:IsA("BasePart") and p ~= m.PrimaryPart then
					local w2 = Instance.new("WeldConstraint")
					w2.Part0, w2.Part1 = m.PrimaryPart, p
					w2.Parent = p
				end
			end
			m:PivotTo(hand.CFrame * wld.C0)
			setTr(m, 1)
			m.Parent = char
			table.insert(h.models, m)
			flash(hand, c)
			local v = Instance.new("NumberValue")
			v.Value = 1
			v.Changed:Connect(function(a)
				setTr(m, a)
			end)
			TweenService:Create(v, TweenInfo.new(0.12), { Value = 0 }):Play()
			task.delay(0.2, v.Destroy, v)
		end
	end
end
local function dismissStep(now)
	for char, h in held do
		if now > h.until or not char.Parent then
			held[char] = nil
			for _, m in h.models do
				local v = Instance.new("NumberValue")
				v.Changed:Connect(function(a)
					setTr(m, a)
				end)
				TweenService:Create(v, TweenInfo.new(0.2), { Value = 1 }):Play()
				task.delay(0.22, function()
					v:Destroy()
					m:Destroy()
				end)
			end
		end
	end
end

------------------------------------------------------------------------ playback
local tracks = {} -- [char] = track
local motorsOf = setmetatable({}, { __mode = "k" })
local lastOut = setmetatable({}, { __mode = "k" }) -- [Motor6D] = CFrame we wrote last frame
local FPS = 60

local function motors(char)
	local m = motorsOf[char]
	if m ~= nil then
		return m or nil
	end
	local hum = char:FindFirstChildOfClass("Humanoid")
	if not hum or hum.RigType ~= Enum.HumanoidRigType.R15 then
		motorsOf[char] = false
		return nil
	end
	m = {}
	for joint, part in PART do
		local p = char:FindFirstChild(part)
		local mo = p and p:FindFirstChild(joint)
		if mo and mo:IsA("Motor6D") then
			m[joint] = mo
		end
	end
	if not m.Root or not m.Waist then
		return nil
	end
	motorsOf[char] = m
	return m
end

-- opts: impactAt (s, time until first impact), hits, amp, spd, flourish
function CharAnim.PlayClip(char, name, opts)
	local c = CLIPS[name]
	local m = char and motors(char)
	if not c or not m then
		return nil
	end
	opts = opts or {}
	local i1 = c.i[1] or c.w
	local T1 = math.max(opts.impactAt or i1 / FPS, 0.03)
	local hits = (c.la and opts.hits and opts.hits > 1) and opts.hits or 1
	local spd = opts.spd or 1
	if hits > 1 then
		spd = 1 -- the loop must stay locked to the server's 0.3 s hit spacing
	end
	local prev = tracks[char]
	local from = nil
	if prev then
		from = {}
		for j, mo in m do
			from[j] = lastOut[mo]
		end
	end
	local tr = {
		clip = c, name = name, t0 = os.clock(), T1 = T1, i1 = i1, hits = hits, spd = spd, amp = opts.amp or 1,
		extra = (hits - 1) * 18, from = from, m = m, hum = char:FindFirstChildOfClass("Humanoid"), dash = opts.dash,
		flourish = opts.flourish,
	}
	tr.total = T1 + ((c.n - i1) / spd + tr.extra) / FPS
	tracks[char] = tr
	return tr
end

-- returns authored frame, blend weight
local function frameAt(tr, t)
	local c = tr.clip
	if t < tr.T1 then
		return tr.i1 * (t / tr.T1), math.clamp(t / math.min(0.08, tr.T1 * 0.6), 0, 1)
	end
	local u = (t - tr.T1) * FPS
	if u < tr.extra then
		return c.la + (u % 18), 1
	end
	local f = tr.i1 + (u - tr.extra) * tr.spd
	local w = 1
	if f > c.r and c.n > c.r then
		w = 1 - (f - c.r) / (c.n - c.r)
		w = w * w * (3 - 2 * w)
	end
	return math.min(f, c.n), w
end

local function step()
	local now = os.clock()
	for char, tr in tracks do
		local t = now - tr.t0
		if t >= tr.total or not char.Parent or not tr.hum or tr.hum.Health <= 0 then
			tracks[char] = nil
			for _, mo in tr.m do
				if lastOut[mo] and mo.Transform == lastOut[mo] then
					mo.Transform = CFrame.identity -- the Animator didn't own it; don't leave it posed
				end
				lastOut[mo] = nil
			end
			if tr.flourish and char.Parent and tr.hum and tr.hum.Health > 0 then
				CharAnim.PlayClip(char, "Pose_Cool", { amp = 1 })
			end
			continue
		end
		local f, w = frameAt(tr, t)
		local moving = tr.hum.MoveDirection.Magnitude > 0.1 and not tr.dash
		local legW = moving and 0.25 or 1
		local c = tr.clip
		local xf = tr.from and math.clamp(t / 0.08, 0, 1) or 1
		for j, mo in tr.m do
			local base = mo.Transform
			if lastOut[mo] and base == lastOut[mo] then
				base = CFrame.identity
			end
			local jt = c.j[j]
			local cf = jt and sample(jt, f, lerpCF) or CFrame.identity
			if j == "Root" and c.p then
				local pos = sample(c.p, f, lerpV)
				if moving then
					pos = Vector3.new(pos.X, pos.Y * legW, pos.Z) * 0.5
				end
				cf = CFrame.new(pos) * cf
			end
			if tr.amp ~= 1 then
				cf = CFrame.identity:Lerp(cf, tr.amp)
			end
			local jw = w * ((LEGS[j] and legW) or 1)
			local out = base:Lerp(cf, jw)
			if xf < 1 and tr.from and tr.from[j] then
				out = tr.from[j]:Lerp(out, xf)
			end
			mo.Transform = out
			lastOut[mo] = out
		end
	end
	dismissStep(now)
end

------------------------------------------------------------------------ public: play a move
-- info: { who = userId, pid, slot, kind, dir, ci = combo index, w = windup seconds, hits, impactAt = seconds }
local Abilities
function CharAnim.PlayMove(char, info)
	if not char then
		return
	end
	local def = Powers.ById[info.pid]
	local ab = def and def.Kit and def.Kit[info.slot]
	local kind = info.kind or (ab and ab.Kind) or "Punch"
	local name = CharAnim.ClipName(info.pid, info.slot, kind, info.ci)
	if not name then
		return
	end
	local st = CharAnim.StyleOf(info.pid)
	local amp = st.amp or 1
	if info.slot == "G" then
		amp = 1.08
	end
	local flourish = def and RANK[def.Rarity] and (info.slot == "R" or info.slot == "G")
	local tr = CharAnim.PlayClip(char, name, {
		impactAt = info.impactAt or info.w, hits = info.hits or (ab and ab.Hits), amp = amp, spd = st.spd,
		dash = kind == "Dash", flourish = flourish,
	})
	if tr then
		summon(char, info.pid, tr.total + 0.15)
	end
	return tr
end

function CharAnim.Init()
	RunService.Stepped:Connect(step)
end

return CharAnim
